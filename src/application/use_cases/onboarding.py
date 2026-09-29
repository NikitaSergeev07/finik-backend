"""Device authentication, separate demo identities, and owl onboarding."""

import hashlib
from uuid import UUID, uuid4

from application.dto import GameState
from application.ports import UnitOfWork
from application.use_cases._common import load_state
from application.use_cases.calendar import initialize_clock, new_week, validate_timezone
from core.errors import Conflict, RuleViolation
from domain import rules
from domain.entities import Goal, LogEntry, Pet, Player, Purchase, TaskProgress
from domain.enums import ActionKind, Category, Species
from domain.services.look import validate_accessories
from domain.services.planning import apply_plan


async def register_device(
    uow: UnitOfWork,
    device_id: str,
    *,
    timezone: str = "UTC",
    mode: str = "normal",
    demo_preset: str | None = None,
) -> Player:
    validate_timezone(timezone)
    if mode not in ("normal", "demo"):
        raise RuleViolation("Неизвестный режим игры")
    if demo_preset is not None and (mode != "demo" or demo_preset not in ("new", "prepared")):
        raise RuleViolation("Сценарий доступен только в деморежиме")
    identity = f"{mode}:{hashlib.sha256(device_id.encode()).hexdigest()}"
    async with uow:
        player = await uow.players.get_by_device(identity)
        if player is None:
            player = Player(
                uuid4(), identity, rules.INCOME_OPTIONS[1], 0, timezone=timezone, mode=mode
            )
            await uow.players.add(player)
        else:
            player = await uow.players.get(player.id)
            assert player is not None
        if demo_preset:
            await uow.players.wipe_progress(player.id)
            player.free_coins = 0
            player.vaccinated_until = 0
            player.unlocked_shop = []
            player.clock = {}
            player.timezone = timezone
            player.selected_goal_slug = rules.GOAL_CATALOG[0].slug
        elif await uow.pets.get_by_player(player.id) is None:
            player.timezone = timezone
        await uow.players.save(player)
        await uow.commit()
    if demo_preset == "prepared":
        await create_pet(uow, player.id, "Финик", Species.OWL, 60, look_variant=0)
        async with uow:
            state = await load_state(uow, player.id)
            apply_plan(
                state.player,
                state.week,
                {
                    Category.FOOD: 12,
                    Category.WATER: 10,
                    Category.PLAY: 14,
                    Category.SAVE: 12,
                },
            )
            state.week.plan_confirmed = True
            state.pet.xp = 160
            state.pet.needs = {cat: 85 for cat in Category if cat.is_need}
            state.pet.accessories = ["hat", "bandana"]
            state.pet.equipped_accessory = "hat_leaf"
            state.goal.saved = 35
            await uow.shop.add_purchase(Purchase(uuid4(), player.id, state.week.id, "hat_leaf", 0))
            for task in await uow.tasks.list_defs():
                questions = await uow.tasks.list_questions(task.slug)
                if questions:
                    await uow.tasks.upsert_progress(
                        TaskProgress(
                            player.id,
                            state.week.id,
                            task.slug,
                            progress=1,
                            data={"answered": [questions[0].slug]},
                        )
                    )
                    break
            await uow.players.save(state.player)
            await uow.pets.save(state.pet)
            await uow.goals.save(state.goal)
            await uow.weeks.save(state.week)
            await uow.commit()
    return player


async def create_pet(
    uow: UnitOfWork,
    player_id: UUID,
    name: str,
    species: Species,
    weekly_income: int,
    *,
    goal_slug: str | None = None,
    look_variant: int = 0,
    accessories: list[str] | None = None,
) -> GameState:
    if weekly_income not in rules.INCOME_OPTIONS:
        raise RuleViolation(f"Доход в неделю бывает только {rules.INCOME_OPTIONS}")
    name = name.strip()
    if not 1 <= len(name) <= 20:
        raise RuleViolation("Имя питомца — от 1 до 20 символов")
    option = rules.goal_by_slug(goal_slug)
    look = rules.look_variant_or_raise(look_variant)
    chosen_accessories = validate_accessories(accessories or [])
    async with uow:
        player = await uow.players.get(player_id)
        if player is None:
            raise Conflict("Сначала войди по устройству")
        if await uow.pets.get_by_player(player_id) is not None:
            raise Conflict("Питомец уже есть")
        player.weekly_income = weekly_income
        player.free_coins = weekly_income
        player.selected_goal_slug = option.slug
        day = initialize_clock(player)
        pet = Pet(
            uuid4(),
            player_id,
            name,
            Species.OWL,
            0,
            {cat: rules.NEED_START for cat in Category if cat.is_need},
            look_variant=look,
            accessories=chosen_accessories,
        )
        week = new_week(player, 1, day, income=weekly_income)
        goals = [
            Goal(uuid4(), player_id, item.title, item.target, 0, catalog_slug=item.slug)
            for item in rules.GOAL_CATALOG
        ]
        goal = next(item for item in goals if item.catalog_slug == option.slug)
        await uow.pets.add(pet)
        await uow.weeks.add(week)
        for item in goals:
            await uow.goals.add(item)
        await uow.players.save(player)
        await uow.log.add(
            LogEntry(
                player_id,
                week.id,
                week.day,
                ActionKind.INCOME,
                amount=weekly_income,
                note=f"Пришёл доход {weekly_income}",
            )
        )
        await uow.commit()
        return GameState(
            player,
            pet,
            week,
            goal,
            last_income=weekly_income,
            last_income_note=f"Пришёл доход {weekly_income}",
            goals=tuple(goals),
        )


async def select_goal(uow: UnitOfWork, player_id: UUID, slug: str) -> GameState:
    option = rules.goal_by_slug(slug)
    async with uow:
        state = await load_state(uow, player_id)
        goals = list(state.goals)
        goal = next((item for item in goals if item.catalog_slug == slug), None)
        if goal is None:
            goal = Goal(uuid4(), player_id, option.title, option.target, 0, catalog_slug=slug)
            await uow.goals.add(goal)
        state.player.selected_goal_slug = slug
        await uow.players.save(state.player)
        await uow.commit()
    async with uow:
        return await load_state(uow, player_id)
