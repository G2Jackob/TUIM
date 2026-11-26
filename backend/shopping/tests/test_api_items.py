import uuid
from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def shared(alice, bob, make_list):
    return make_list(alice, members=[bob])


def url(lst, item=None, action=""):
    base = f"/api/lists/{lst.id}/items/"
    if item is not None:
        base += f"{item.id}/"
    return base + (f"{action}/" if action else "")


# ---- dodawanie


def test_member_adds_item_with_all_fields(bob, shared):
    response = bob.client.post(
        url(shared),
        {
            "name": " Mleko ",
            "quantity": "2",
            "unit": "l",
            "category": "Nabiał",
            "estimated_price": "3.49",
            "note": "bez laktozy",
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Mleko"
    assert Decimal(body["quantity"]) == 2
    assert body["unit"] == "l"
    assert body["category"] == "Nabiał"
    assert body["estimated_price"] == "3.49"
    assert body["reserved_by"] is None and body["is_purchased"] is False
    assert body["list_id"] == str(shared.id)


def test_item_defaults(alice, make_list):
    lst = make_list(alice)
    body = alice.client.post(url(lst), {"name": "Chleb"}, format="json").json()
    assert Decimal(body["quantity"]) == 1
    assert body["unit"] == "szt"
    assert body["estimated_price"] is None


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_rejected_with_readable_message(alice, make_list, name):
    lst = make_list(alice)
    response = alice.client.post(url(lst), {"name": name}, format="json")
    assert response.status_code == 400
    assert response.json()["name"] == ["Nazwa produktu nie może być pusta."]


def test_name_is_required(alice, make_list):
    lst = make_list(alice)
    assert alice.client.post(url(lst), {"quantity": 1}, format="json").status_code == 400


@pytest.mark.parametrize("quantity", ["0", "-1", "-0.5"])
def test_non_positive_quantity_is_rejected(alice, make_list, quantity):
    lst = make_list(alice)
    response = alice.client.post(url(lst), {"name": "x", "quantity": quantity}, format="json")
    assert response.status_code == 400
    assert response.json()["quantity"] == ["Ilość musi być większa od zera."]


def test_non_numeric_quantity_is_rejected(alice, make_list):
    lst = make_list(alice)
    response = alice.client.post(url(lst), {"name": "x", "quantity": "dużo"}, format="json")
    assert response.status_code == 400 and "quantity" in response.json()


def test_negative_price_is_rejected(alice, make_list):
    lst = make_list(alice)
    response = alice.client.post(url(lst), {"name": "x", "estimated_price": "-1"}, format="json")
    assert response.status_code == 400
    assert response.json()["estimated_price"] == ["Cena nie może być ujemna."]


def test_zero_price_and_null_price_are_allowed(alice, make_list):
    lst = make_list(alice)
    assert alice.client.post(url(lst), {"name": "x", "estimated_price": "0"}, format="json").status_code == 201
    assert alice.client.post(url(lst), {"name": "y", "estimated_price": None}, format="json").status_code == 201


def test_unknown_unit_is_rejected(alice, make_list):
    lst = make_list(alice)
    assert alice.client.post(url(lst), {"name": "x", "unit": "garść"}, format="json").status_code == 400


def test_client_cannot_set_reservation_fields_on_create(alice, bob, make_list):
    lst = make_list(alice)
    response = alice.client.post(
        url(lst),
        {"name": "x", "is_purchased": True, "reserved_by": bob.user.id},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["is_purchased"] is False
    assert response.json()["reserved_by"] is None


# ---- dostęp


def test_stranger_cannot_read_or_write_items(alice, carol, make_list, make_item):
    lst = make_list(alice)
    item = make_item(lst)
    assert carol.client.get(url(lst)).status_code == 403
    assert carol.client.get(url(lst, item)).status_code == 403
    assert carol.client.post(url(lst), {"name": "x"}, format="json").status_code == 403
    assert carol.client.patch(url(lst, item), {"name": "x"}, format="json").status_code == 403
    assert carol.client.delete(url(lst, item)).status_code == 403
    assert carol.client.post(url(lst, item, "reserve")).status_code == 403


def test_items_of_unknown_list_is_404(alice):
    assert alice.client.get(f"/api/lists/{uuid.uuid4()}/items/").status_code == 404


def test_item_from_other_list_is_404(alice, make_list, make_item):
    lst1, lst2 = make_list(alice, "A"), make_list(alice, "B")
    item = make_item(lst2)
    assert alice.client.get(url(lst1, item)).status_code == 404
    assert alice.client.post(url(lst1, item, "reserve")).status_code == 404


# ---- odczyt / edycja / usuwanie


def test_list_items_in_list_only(alice, make_list, make_item):
    lst, other = make_list(alice, "A"), make_list(alice, "B")
    make_item(lst, "jabłka")
    make_item(other, "obce")
    names = [i["name"] for i in alice.client.get(url(lst)).json()]
    assert names == ["jabłka"]


def test_purchased_items_are_listed_last(alice, make_list, make_item):
    lst = make_list(alice)
    make_item(lst, "kupione", is_purchased=True)
    make_item(lst, "do kupienia")
    assert [i["name"] for i in alice.client.get(url(lst)).json()] == ["do kupienia", "kupione"]


def test_member_edits_item(bob, shared, make_item):
    item = make_item(shared)
    response = bob.client.patch(
        url(shared, item), {"quantity": "5", "name": "Mleko 3.2%", "estimated_price": "4.20"}, format="json"
    )
    assert response.status_code == 200
    assert Decimal(response.json()["quantity"]) == 5
    assert response.json()["name"] == "Mleko 3.2%"


def test_edit_validates_input(bob, shared, make_item):
    item = make_item(shared)
    assert bob.client.patch(url(shared, item), {"name": ""}, format="json").status_code == 400
    assert bob.client.patch(url(shared, item), {"quantity": "0"}, format="json").status_code == 400


def test_member_deletes_item(bob, shared, make_item):
    item = make_item(shared)
    assert bob.client.delete(url(shared, item)).status_code == 204
    assert bob.client.get(url(shared, item)).status_code == 404


# ---- lista zarchiwizowana jest tylko do odczytu


def test_archived_list_rejects_changes_but_allows_reading(alice, make_list, make_item):
    lst = make_list(alice, is_archived=True)
    item = make_item(lst)
    assert alice.client.get(url(lst)).status_code == 200
    assert alice.client.get(url(lst, item)).status_code == 200
    assert alice.client.post(url(lst), {"name": "x"}, format="json").status_code == 409
    assert alice.client.patch(url(lst, item), {"name": "x"}, format="json").status_code == 409
    assert alice.client.delete(url(lst, item)).status_code == 409
    assert alice.client.post(url(lst, item, "reserve")).status_code == 409


# ---- rezerwacja / zakup po HTTP


def test_reserve_flow_over_http(alice, bob, shared, make_item):
    item = make_item(shared)
    response = bob.client.post(url(shared, item, "reserve"))
    assert response.status_code == 200
    assert response.json()["reserved_by"]["username"] == "bob"

    # ktoś inny nie może przejąć
    conflict = alice.client.post(url(shared, item, "reserve"))
    assert conflict.status_code == 409

    # po zwolnieniu może
    assert bob.client.post(url(shared, item, "release")).status_code == 200
    assert alice.client.post(url(shared, item, "reserve")).json()["reserved_by"]["username"] == "alice"


def test_release_by_non_reserver_member_is_403(alice, bob, carol, make_list, make_item):
    lst = make_list(alice, members=[bob, carol])
    item = make_item(lst)
    bob.client.post(url(lst, item, "reserve"))
    assert carol.client.post(url(lst, item, "release")).status_code == 403
    assert alice.client.post(url(lst, item, "release")).status_code == 200  # właściciel może


def test_release_unreserved_is_409(bob, shared, make_item):
    item = make_item(shared)
    assert bob.client.post(url(shared, item, "release")).status_code == 409


def test_purchase_and_undo_over_http(alice, bob, shared, make_item):
    item = make_item(shared)
    bought = bob.client.post(url(shared, item, "purchase"))
    assert bought.status_code == 200
    assert bought.json()["is_purchased"] is True
    assert bought.json()["purchased_by"]["username"] == "bob"

    assert alice.client.post(url(shared, item, "purchase")).status_code == 409  # już kupione

    undone = bob.client.post(url(shared, item, "unpurchase"))
    assert undone.status_code == 200 and undone.json()["is_purchased"] is False
    assert bob.client.post(url(shared, item, "unpurchase")).status_code == 409  # nie jest kupione


def test_purchase_blocked_by_other_users_reservation(alice, bob, shared, make_item):
    item = make_item(shared)
    bob.client.post(url(shared, item, "reserve"))
    assert alice.client.post(url(shared, item, "purchase")).status_code == 409
    assert bob.client.post(url(shared, item, "purchase")).status_code == 200


def test_unpurchase_by_other_member_is_403(alice, bob, carol, make_list, make_item):
    lst = make_list(alice, members=[bob, carol])
    item = make_item(lst)
    bob.client.post(url(lst, item, "purchase"))
    assert carol.client.post(url(lst, item, "unpurchase")).status_code == 403
    assert alice.client.post(url(lst, item, "unpurchase")).status_code == 200


def test_actions_accept_only_post(bob, shared, make_item):
    item = make_item(shared)
    assert bob.client.get(url(shared, item, "reserve")).status_code == 405
