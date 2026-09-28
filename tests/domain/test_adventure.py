"""Adventure choices have costs and visible educational consequences."""

import pytest

from domain.services.adventure import EPISODES, new_game, play, scene


def test_budget_market_surprise_and_saving() -> None:
    episode = EPISODES["adventure_market"]
    state = new_game(episode)
    assert scene(episode, state)["kind"] == "BUDGET"
    play(episode, state, food=6, water=4, reserve=6)
    assert (state.stage, state.wallet, state.reserve, state.care) == (1, 14, 6, 2)
    play(episode, state, choice_id="pot")
    assert (state.wallet, state.joy) == (5, 2)
    play(episode, state, choice_id="reserve")
    assert (state.wallet, state.reserve) == (5, 1)
    play(episode, state, choice_id="report")
    play(episode, state, amount=4)
    assert (state.stage, state.wallet, state.dream) == (5, 1, 4)
    assert scene(episode, state)["kind"] == "RESULT"


def test_spending_more_than_wallet_is_rejected_without_advancing() -> None:
    episode = EPISODES["adventure_storm"]
    state = new_game(episode)
    with pytest.raises(ValueError):
        play(episode, state, food=20, water=20, reserve=10)
    assert (state.stage, state.wallet) == (0, episode.wallet)
