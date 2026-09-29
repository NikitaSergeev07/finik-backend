"""Покупка и надевание нарядов: из статьи игр, только своё."""

from httpx import AsyncClient

from tests.api.test_tz_mandatory import start


async def test_buy_pot_and_accessory_then_customize(client: AsyncClient):
    h = await start(client)
    r = await client.put(
        "/api/v1/plan", headers=h, json={"food": 10, "water": 8, "play": 14, "save": 8}
    )
    assert r.status_code == 200

    await client.post("/api/v1/plan/confirm", headers=h)
    r = await client.post("/api/v1/shop/buy", headers=h, json={"slug": "pot_blue"})
    assert r.status_code == 200, r.text
    pet = r.json()["state"]["pet"]
    assert pet["equipped_pot"] == "pot_blue"
    assert "pot_blue" in r.json()["state"]["owned_cosmetics"]
    play = next(e for e in r.json()["state"]["week"]["entries"] if e["category"] == "PLAY")
    assert play["spent"] == 3

    r = await client.post("/api/v1/shop/buy", headers=h, json={"slug": "scarf_knit"})
    assert r.status_code == 200, r.text
    body = r.json()["state"]
    assert body["pet"]["equipped_accessory"] == "scarf_knit"
    assert body["pet"]["equipped_pot"] == "pot_blue"

    r = await client.post("/api/v1/shop/buy", headers=h, json={"slug": "pot_blue"})
    assert r.status_code == 422
    assert "уже у тебя" in r.json()["error"]["message"]

    r = await client.post("/api/v1/pet/customize", headers=h, json={"pot": ""})
    assert r.status_code == 200
    assert r.json()["pet"]["equipped_pot"] == ""
    assert r.json()["pet"]["equipped_accessory"] == "scarf_knit"

    r = await client.post(
        "/api/v1/pet/customize",
        headers=h,
        json={"pot": "pot_blue", "look_variant": 1},
    )
    assert r.status_code == 200
    assert r.json()["pet"]["equipped_pot"] == "pot_blue"
    assert r.json()["pet"]["look_variant"] == 1

    r = await client.post("/api/v1/pet/customize", headers=h, json={"accessory": "hat_leaf"})
    assert r.status_code == 422
    assert "лавк" in r.json()["error"]["message"].lower()

    state = (await client.get("/api/v1/state", headers=h)).json()
    assert state["pet"]["equipped_pot"] == "pot_blue"
    assert "scarf_knit" in state["owned_cosmetics"]

    shelf = {i["slug"]: i for i in (await client.get("/api/v1/shop/items", headers=h)).json()}
    assert shelf["pot_blue"]["owned"] is True and shelf["pot_blue"]["equipped"] is True
    assert shelf["pot_blue"]["slot"] == "pot"
    assert shelf["hat_leaf"]["owned"] is False
    assert shelf["ball"]["slot"] == ""
