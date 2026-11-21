"""Regression coverage for user defaults and actual trade exits."""

import json
from decimal import Decimal

import pytest

from src.models import FavoriteProduct, TradePartialExit, User, db


class TestCreateTradePnl:
    """Verify P&L uses the trade owner's settings and actual fills."""

    @pytest.mark.parametrize("own_favorite", [False, True])
    def test_favorite_defaults_are_user_scoped(
        self, app, auth_client, sample_trade_data, default_user, own_favorite
    ):
        """Another user's matching symbol cannot influence fees or P&L."""
        with app.app_context():
            other = User(email="other-pnl@example.test", name="Other")
            db.session.add(other)
            db.session.flush()
            db.session.add(FavoriteProduct(
                user_id=other.id, symbol="TEST", point_value=10, fees=7
            ))
            db.session.commit()
            if own_favorite:
                db.session.add(FavoriteProduct(
                    user_id=default_user, symbol="TEST", point_value=2, fees=3
                ))
                db.session.commit()

        payload = dict(sample_trade_data, symbol="TEST", entry_price=100,
                       stop_loss=90, take_profit=110, position_size=1)
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        trade = response.get_json()
        assert trade["fees"] == (3 if own_favorite else 0)
        assert trade["pnl"] == (17 if own_favorite else 10)

    @pytest.mark.parametrize(
        "direction,exit_price,pnl,outcome",
        [("long", 110, 15, "win"), ("short", 90, 15, "win"),
         ("long", 90, -25, "loss"), ("short", 110, -25, "loss"),
         ("long", 100, -5, "break_even")],
    )
    def test_actual_exit_price(
        self, auth_client, sample_trade_data, direction, exit_price, pnl, outcome
    ):
        """An actual exit produces P&L and an outcome without a target."""
        payload = dict(sample_trade_data, direction=direction, entry_price=100,
                       stop_loss=None, exit_price=exit_price, position_size=2, fees=5)
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        trade = response.get_json()
        assert trade["pnl"] == pnl
        assert trade["outcome"] == outcome

    def test_actual_exit_overrides_planned_loss(self, auth_client, sample_trade_data):
        """A supplied fill is used instead of an assumed stop-loss fill."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       take_profit=120, exit_price=95, position_size=2,
                       fees=5, outcome="LOSS")
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        assert response.get_json()["pnl"] == -15

    def test_zero_pnl_is_preserved(self, auth_client, sample_trade_data):
        """An exactly flat net result is serialized as zero rather than missing."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       exit_price=105, position_size=1, fees=5)
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        assert response.get_json()["pnl"] == 0

    def test_partial_exit_with_actual_remaining_fill(
        self, auth_client, sample_trade_data
    ):
        """The remainder uses the actual exit rather than the planned target."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       take_profit=130, exit_price=120, position_size=2, fees=0,
                       exit_transactions=[{"qty": 1, "exit_price": 110, "fees": 2}])
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        trade_id = response.get_json()["id"]
        assert response.get_json()["pnl"] == 28
        # Recalculation after persistence exercises the normalized exit records.
        updated = auth_client.put(
            f"/api/trades/{trade_id}", data=json.dumps({"notes": "Recalculate"}),
            content_type="application/json",
        )
        assert updated.status_code == 200
        assert updated.get_json()["pnl"] == 28

    @pytest.mark.parametrize("exit_price", [-1, 0, "invalid", "NaN", "Infinity"])
    def test_invalid_actual_exit(self, auth_client, sample_trade_data, exit_price):
        """Invalid actual prices fail validation on creation and editing."""
        response = auth_client.post(
            "/api/trades",
            data=json.dumps(dict(sample_trade_data, exit_price=exit_price)),
            content_type="application/json",
        )
        assert response.status_code == 400
        created = auth_client.post(
            "/api/trades", data=json.dumps(sample_trade_data),
            content_type="application/json",
        )
        assert created.status_code == 201
        trade_id = created.get_json()["id"]
        response = auth_client.put(
            f"/api/trades/{trade_id}", data=json.dumps({"exit_price": exit_price}),
            content_type="application/json",
        )
        assert response.status_code == 400


class TestUpdateTradePnl:
    """Verify edits persist the exits used to calculate P&L."""

    def test_replace_and_clear_partial_exits(self, app, auth_client, sample_trade_data):
        """Replacing and clearing exits updates both storage and calculated P&L."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       position_size=1, take_profit=130, fees=0,
                       exit_transactions=[{"qty": 1, "exit_price": 110, "fees": 0}])
        response = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert response.status_code == 201
        trade_id = response.get_json()["id"]
        assert response.get_json()["pnl"] == 10

        for exits, expected in [
            ([{"qty": 1, "exit_price": 120, "fees": 2}], 18), ([], 30)
        ]:
            response = auth_client.put(
                f"/api/trades/{trade_id}",
                data=json.dumps({"exit_transactions": exits}),
                content_type="application/json",
            )
            assert response.status_code == 200
            assert response.get_json()["pnl"] == expected
            saved = auth_client.get(f"/api/trades/{trade_id}").get_json()
            assert saved["pnl"] == expected
            with app.app_context():
                rows = TradePartialExit.query.filter_by(trade_id=trade_id).all()
                assert len(rows) == len(exits)
                if rows:
                    assert rows[0].exit_price == Decimal("120")
                    assert rows[0].fees == Decimal("2")

    def test_update_actual_exit(self, auth_client, sample_trade_data):
        """Closing an open trade through an exit-price edit recalculates P&L."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       position_size=1, fees=2)
        created = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert created.status_code == 201
        trade_id = created.get_json()["id"]
        response = auth_client.put(
            f"/api/trades/{trade_id}", data=json.dumps({"exit_price": 95}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.get_json()["exit_price"] == 95
        assert response.get_json()["pnl"] == -7
        assert response.get_json()["outcome"] == "loss"

    @pytest.mark.parametrize("closing_data,cleared_data", [
        ({"exit_price": 110}, {"exit_price": None}),
        ({"exit_transactions": [{"qty": 1, "exit_price": 110}]},
         {"exit_transactions": []}),
    ])
    def test_removing_last_exit_reopens_trade(
        self, auth_client, sample_trade_data, closing_data, cleared_data
    ):
        """Removing the last fill clears closed status and its timestamp."""
        payload = dict(sample_trade_data, entry_price=100, stop_loss=90,
                       position_size=1, fees=0, **closing_data)
        created = auth_client.post(
            "/api/trades", data=json.dumps(payload), content_type="application/json"
        )
        assert created.status_code == 201
        trade_id = created.get_json()["id"]
        response = auth_client.put(
            f"/api/trades/{trade_id}", data=json.dumps(cleared_data),
            content_type="application/json",
        )
        assert response.status_code == 200
        trade = response.get_json()
        assert trade["status"] == "confirmed"
        assert trade["pnl"] is None
        assert trade["exited_at"] is None
