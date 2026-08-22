"""NSGA-II multi-objective optimizer.

Population is ranked by Pareto dominance into fronts; within a front, crowding
distance preserves diversity.  ``portfolio_size`` keeps joint-mode symbol genomes
at an exact user-selected N.  ``early_stop_generations`` stops when the Pareto
front has not materially changed for a configurable number of generations.
"""

from __future__ import annotations

import random

from ..candidate import Candidate
from .operators import crossover, mutate


def dominates(a, b) -> bool:
    better = False
    for x, y in zip(a, b):
        if x < y - 1e-12:
            return False
        if x > y + 1e-12:
            better = True
    return better


def fast_non_dominated_sort(fitness: list[list[float]]) -> list[list[int]]:
    n = len(fitness)
    dominated_by = [[] for _ in range(n)]
    domination_count = [0] * n
    fronts: list[list[int]] = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates(fitness[p], fitness[q]):
                dominated_by[p].append(q)
            elif dominates(fitness[q], fitness[p]):
                domination_count[p] += 1
        if domination_count[p] == 0:
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        nxt: list[int] = []
        for p in fronts[i]:
            for q in dominated_by[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    fronts.pop()
    return fronts


def crowding_distance(front_indices: list[int], fitness: list[list[float]]) -> dict[int, float]:
    dist = {idx: 0.0 for idx in front_indices}
    if not front_indices:
        return dist
    m = len(fitness[0])
    for o in range(m):
        ordered = sorted(front_indices, key=lambda idx: fitness[idx][o])
        dist[ordered[0]] = float("inf")
        dist[ordered[-1]] = float("inf")
        fmin = fitness[ordered[0]][o]
        fmax = fitness[ordered[-1]][o]
        span = fmax - fmin
        if span <= 1e-12:
            continue
        for k in range(1, len(ordered) - 1):
            dist[ordered[k]] += (fitness[ordered[k + 1]][o] - fitness[ordered[k - 1]][o]) / span
    return dist


def _rank_select(pop, fitness, rng: random.Random, fronts, crowd, k=2):
    best = None
    for _ in range(k):
        cand = rng.randrange(len(pop))
        if best is None:
            best = cand
        else:
            f1, f2 = _front_of(cand, fronts), _front_of(best, fronts)
            if f1 < f2:
                best = cand
            elif f1 == f2 and crowd[cand] > crowd[best]:
                best = cand
    return pop[best], fitness[best]


def _front_of(idx, fronts):
    for rank, front in enumerate(fronts):
        if idx in front:
            return rank
    return len(fronts)


def select_parents(pop, fitness, rng: random.Random, fronts, crowd):
    p1, _ = _rank_select(pop, fitness, rng, fronts, crowd)
    p2, _ = _rank_select(pop, fitness, rng, fronts, crowd)
    return p1, p2


def _front_signature(pop, fitness, front):
    """Stable, rounded signature used only for optional early stopping."""
    rows = []
    for idx in front:
        rows.append((pop[idx].key(), tuple(round(float(v), 4) for v in fitness[idx])))
    return tuple(sorted(rows))


def nsga2(
    initial_population: list[Candidate],
    evaluate,
    universe: list[str],
    rng: random.Random,
    population_size: int = 200,
    generations: int = 100,
    crossover_prob: float = 0.9,
    mutation_prob: float = 0.4,
    min_gap: int = 40,
    max_day: int = 252,
    progress: bool = True,
    fixed_symbols: list[str] | None = None,
    portfolio_size: int | None = None,
    early_stop_generations: int | None = 15,
    evaluate_many=None,
):
    """Run NSGA-II; all objective values are maximised.

    ``evaluate_many`` may evaluate a generation concurrently. The algorithm,
    RNG sequence, Pareto sorting and selection criteria are otherwise unchanged.
    """
    pop = list(initial_population)
    fitness = evaluate_many(pop) if evaluate_many else [evaluate(c) for c in pop]

    front_sizes = []
    last_signature = None
    stable_generations = 0

    for gen in range(generations):
        fronts = fast_non_dominated_sort(fitness)
        crowd = {}
        for front in fronts:
            crowd.update(crowding_distance(front, fitness))
        front_sizes.append([len(f) for f in fronts])

        offspring: list[Candidate] = []
        seen_offspring = set()
        attempts = 0
        while len(offspring) < population_size and attempts < population_size * 20:
            attempts += 1
            p1, p2 = select_parents(pop, fitness, rng, fronts, crowd)
            child = None
            if rng.random() < crossover_prob:
                child = crossover(
                    p1, p2, universe, rng, min_gap, max_day, fixed_symbols, portfolio_size
                )
            if child is None:
                child = p1 if rng.random() < 0.5 else p2
            if rng.random() < mutation_prob:
                m = mutate(
                    child, universe, rng, min_gap, max_day, fixed_symbols, portfolio_size
                )
                if m is not None:
                    child = m
            if child.key() in seen_offspring:
                continue
            seen_offspring.add(child.key())
            offspring.append(child)

        while len(offspring) < population_size:
            offspring.append(pop[rng.randrange(len(pop))])

        combined = pop + offspring
        offspring_fit = evaluate_many(offspring) if evaluate_many else [evaluate(c) for c in offspring]
        combined_fit = fitness + offspring_fit

        fronts = fast_non_dominated_sort(combined_fit)
        selected: list[Candidate] = []
        selected_fit: list[list[float]] = []
        for front in fronts:
            if len(selected) + len(front) <= population_size:
                for idx in front:
                    selected.append(combined[idx])
                    selected_fit.append(combined_fit[idx])
            else:
                crowd = crowding_distance(front, combined_fit)
                ordered = sorted(front, key=lambda idx: -crowd[idx])
                for idx in ordered[: population_size - len(selected)]:
                    selected.append(combined[idx])
                    selected_fit.append(combined_fit[idx])
                break
            if len(selected) >= population_size:
                break
        pop, fitness = selected, selected_fit

        current_fronts = fast_non_dominated_sort(fitness)
        signature = _front_signature(pop, fitness, current_fronts[0]) if current_fronts else ()
        if signature == last_signature:
            stable_generations += 1
        else:
            stable_generations = 0
            last_signature = signature

        if progress and (gen + 1) % 10 == 0:
            best = max(range(len(fitness)), key=lambda i: fitness[i][0])
            print(
                f"  gen {gen+1}/{generations}: fronts={len(current_fronts)} "
                f"best net_twr_ann={fitness[best][0]:.2f}% {pop[best]}",
                flush=True,
            )

        if early_stop_generations and stable_generations >= early_stop_generations:
            if progress:
                print(
                    f"  NSGA-II early stop at generation {gen+1}: Pareto front unchanged "
                    f"for {stable_generations} generations.",
                    flush=True,
                )
            break

    return pop, fitness, front_sizes
