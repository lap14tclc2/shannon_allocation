"""NSGA-II multi-objective optimizer.

Population is ranked by Pareto dominance into fronts; within a front, crowding
distance preserves diversity. Elitism keeps the best parents each generation.
Symbols and the four allocation times are evolved JOINTLY (crossover and
mutation operate on both parts of the chromosome).
"""

from __future__ import annotations

import random

from ..candidate import Candidate
from .operators import crossover, mutate


def dominates(a, b) -> bool:
    """True if `a` (maximised objectives) weakly dominates `b` and is strictly better somewhere."""
    better = False
    for x, y in zip(a, b):
        if x < y - 1e-12:
            return False
        if x > y + 1e-12:
            better = True
    return better


def fast_non_dominated_sort(fitness: list[list[float]]) -> list[list[int]]:
    """Return a list of fronts (lists of population indices)."""
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
    """Return {index: crowding distance} within a front."""
    dist = {idx: 0.0 for idx in front_indices}
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
):
    """Run NSGA-II. `evaluate(candidate) -> list[float]` (maximised objectives).

    Returns (final_population, fitness_matrix, history_of_pop_sizes_by_front).
    """
    pop = list(initial_population)
    fitness = [evaluate(c) for c in pop]

    front_sizes = []
    for gen in range(generations):
        fronts = fast_non_dominated_sort(fitness)
        crowd = {}
        for front in fronts:
            crowd.update(crowding_distance(front, fitness))
        front_sizes.append([len(f) for f in fronts])

        # Produce offspring.
        offspring: list[Candidate] = []
        while len(offspring) < population_size:
            p1, p2 = select_parents(pop, fitness, rng, fronts, crowd)
            child = None
            if rng.random() < crossover_prob:
                child = crossover(p1, p2, universe, rng, min_gap, max_day)
            if child is None:
                child = p1 if rng.random() < 0.5 else p2
            if rng.random() < mutation_prob:
                m = mutate(child, universe, rng, min_gap, max_day)
                if m is not None:
                    child = m
            offspring.append(child)

        combined = pop + offspring
        combined_fit = fitness + [evaluate(c) for c in offspring]

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

        if progress and (gen + 1) % 10 == 0:
            best = max(range(len(fitness)), key=lambda i: fitness[i][0])
            print(f"  gen {gen+1}/{generations}: fronts={len(fronts)} "
                  f"best net_twr_ann={fitness[best][0]:.2f}% {pop[best]}", flush=True)

    return pop, fitness, front_sizes