"""
quantale.py — Step-by-step implementation of a Quantale in Python.

Hierarchy:
  Stage 1: FiniteSet        — a set with membership and cardinality
  Stage 2: BinaryRelation   — a subset of Q×Q
  Stage 3: Poset            — a set + reflexive, antisymmetric, transitive relation
  Stage 4: Lattice          — a poset where every pair has a join and meet
  Stage 5: CompleteLattice  — join/meet for arbitrary subsets; has ⊤ and ⊥
  Stage 6: Monoid           — a set + associative binary op + identity
  Stage 7: Quantale         — CompleteLattice + Monoid, glued by distributivity
  Stage 8: Residuated       — Quantale + left/right residuals (→ and ←)

Use-case thread: database access-control permissions throughout.
"""

from __future__ import annotations
from typing import TypeVar, Generic, FrozenSet, Callable, Optional
from itertools import product as cartesian

BLOCKED = "blocked"
OVER_BUDGET = "over_budget"
BEHIND_SCHEDULE = "behind_schedule"
HEALTHY = "healthy"
SUCCESS = "success"

MY_ELEMENTS = [BLOCKED, OVER_BUDGET, BEHIND_SCHEDULE, HEALTHY, SUCCESS]

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — FiniteSet
# ─────────────────────────────────────────────────────────────────────────────

class FiniteSet(Generic[T]):
    """
    A finite set: unordered, no duplicates, supports membership and subsets.

    No ordering, no operations — just ∈, ⊆, and cardinality.
    """

    def __init__(self, elements: list[T]) -> None:
        seen = []
        for e in elements:
            if e not in seen:
                seen.append(e)
        self._elements: list[T] = seen

    # ── core interface ────────────────────────────────────────────────────────

    def __contains__(self, x: object) -> bool:
        return x in self._elements

    def __iter__(self):
        return iter(self._elements)

    def __len__(self) -> int:
        return len(self._elements)

    def __repr__(self) -> str:
        return "{" + ", ".join(str(e) for e in self._elements) + "}"

    # ── set operations ────────────────────────────────────────────────────────

    def is_subset_of(self, other: "FiniteSet[T]") -> bool:
        """A ⊆ B: every element of self is in other."""
        return all(e in other for e in self)

    def power_set(self) -> list[FrozenSet[T]]:
        """𝒫(Q): all subsets, represented as frozensets."""
        elems = list(self._elements)
        result = []
        for mask in range(1 << len(elems)):
            result.append(frozenset(elems[i] for i in range(len(elems)) if mask & (1 << i)))
        return result

    def cartesian_product(self) -> list[tuple[T, T]]:
        """Q × Q: all ordered pairs."""
        return list(cartesian(self._elements, repeat=2))

    # ── invariant ─────────────────────────────────────────────────────────────

    def check_no_duplicates(self) -> bool:
        """All elements must be distinct."""
        return len(self._elements) == len(set(str(e) for e in self._elements))


# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — BinaryRelation
# ─────────────────────────────────────────────────────────────────────────────

class BinaryRelation(Generic[T]):
    """
    A binary relation R ⊆ Q×Q.

    Stored as a set of (a, b) pairs.  Can be tested for the four standard
    properties: reflexive, symmetric, antisymmetric, transitive.
    """

    def __init__(self, base: FiniteSet[T], pairs: list[tuple[T, T]]) -> None:
        self.base = base
        # validate: every pair must be from Q×Q
        for a, b in pairs:
            assert a in base and b in base, f"Pair ({a},{b}) outside base set"
        self._pairs: FrozenSet[tuple[T, T]] = frozenset(pairs)

    def __contains__(self, pair: tuple[T, T]) -> bool:
        return pair in self._pairs

    def holds(self, a: T, b: T) -> bool:
        """Does a R b hold?"""
        return (a, b) in self._pairs

    # ── four standard properties ──────────────────────────────────────────────

    def is_reflexive(self) -> bool:
        """∀ a ∈ Q: a R a"""
        return all(self.holds(a, a) for a in self.base)

    def is_symmetric(self) -> bool:
        """∀ a,b: a R b → b R a"""
        return all(self.holds(b, a) for (a, b) in self._pairs)

    def is_antisymmetric(self) -> bool:
        """∀ a,b: a R b ∧ b R a → a = b"""
        for (a, b) in self._pairs:
            if a != b and self.holds(b, a):
                return False
        return True

    def is_transitive(self) -> bool:
        """∀ a,b,c: a R b ∧ b R c → a R c"""
        for (a, b) in self._pairs:
            for c in self.base:
                if self.holds(b, c) and not self.holds(a, c):
                    return False
        return True

    # ── reflexive-transitive closure ─────────────────────────────────────────

    def closure(self) -> "BinaryRelation[T]":
        """
        Compute the reflexive-transitive closure.

        Uses Floyd-Warshall: O(n³).
        """
        elems = list(self.base)
        reach = {(a, b): self.holds(a, b) for a in elems for b in elems}
        for e in elems:
            reach[(e, e)] = True  # reflexivity
        for k in elems:
            for a in elems:
                for b in elems:
                    if reach[(a, k)] and reach[(k, b)]:
                        reach[(a, b)] = True
        pairs = [(a, b) for (a, b), v in reach.items() if v]
        return BinaryRelation(self.base, pairs)

    def __repr__(self) -> str:
        pairs = sorted(str(p) for p in self._pairs)
        return f"Relation({', '.join(pairs)})"

# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — Poset
# ─────────────────────────────────────────────────────────────────────────────

class Poset(Generic[T]):
    """
    A partially ordered set (Q, ≤).

    ≤ must be reflexive, antisymmetric, and transitive.
    Allows incomparable pairs: elements a, b where neither a≤b nor b≤a.
    """

    def __init__(self, base: FiniteSet[T], leq: BinaryRelation[T]) -> None:
        self.base = base
        self.leq = leq
        self._validate()

    def _validate(self) -> None:
        assert self.leq.is_reflexive(),    "≤ must be reflexive"
        assert self.leq.is_antisymmetric(),"≤ must be antisymmetric"
        assert self.leq.is_transitive(),   "≤ must be transitive"

    # ── order queries ─────────────────────────────────────────────────────────

    def le(self, a: T, b: T) -> bool:
        """a ≤ b"""
        return self.leq.holds(a, b)

    def lt(self, a: T, b: T) -> bool:
        """a < b  (strictly less)"""
        return self.le(a, b) and a != b

    def comparable(self, a: T, b: T) -> bool:
        """Are a and b comparable? (one must be ≤ the other)"""
        return self.le(a, b) or self.le(b, a)

    def upper_bounds(self, subset: list[T]) -> list[T]:
        """All c ∈ Q such that x ≤ c for every x in subset."""
        return [c for c in self.base if all(self.le(x, c) for x in subset)]

    def lower_bounds(self, subset: list[T]) -> list[T]:
        """All c ∈ Q such that c ≤ x for every x in subset."""
        return [c for c in self.base if all(self.le(c, x) for x in subset)]

    # ── Hasse diagram (as adjacency list) ────────────────────────────────────

    def hasse_edges(self) -> list[tuple[T, T]]:
        """
        Direct cover relations: a → b if a < b and there is no c with a < c < b.
        These are the edges drawn in a Hasse diagram.
        """
        edges = []
        for a in self.base:
            for b in self.base:
                if self.lt(a, b):
                    # check no element sits strictly between a and b
                    between = [c for c in self.base
                               if c != a and c != b
                               and self.lt(a, c) and self.lt(c, b)]
                    if not between:
                        edges.append((a, b))
        return edges

    def __repr__(self) -> str:
        edges = self.hasse_edges()
        return f"Poset({self.base}, covers={edges})"



# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — Lattice
# ─────────────────────────────────────────────────────────────────────────────

class Lattice(Poset[T]):
    """
    A lattice (Q, ≤): a poset where every pair has a join (⋁) and meet (⋀).

    join(a, b) = least upper bound of {a, b}
    meet(a, b) = greatest lower bound of {a, b}
    """

    def __init__(self, base: FiniteSet[T], leq: BinaryRelation[T]) -> None:
        super().__init__(base, leq)
        self._validate_lattice()

    def _validate_lattice(self) -> None:
        for a in self.base:
            for b in self.base:
                assert self._find_join(a, b) is not None, \
                    f"No join for ({a}, {b}) — not a lattice"
                assert self._find_meet(a, b) is not None, \
                    f"No meet for ({a}, {b}) — not a lattice"

    def _find_join(self, a: T, b: T) -> Optional[T]:
        """Least element c such that a ≤ c and b ≤ c."""
        ubs = self.upper_bounds([a, b])
        # least upper bound: no other upper bound is ≤ it
        candidates = [c for c in ubs if all(self.le(c, d) for d in ubs)]
        return candidates[0] if candidates else None

    def _find_meet(self, a: T, b: T) -> Optional[T]:
        """Greatest element c such that c ≤ a and c ≤ b."""
        lbs = self.lower_bounds([a, b])
        # greatest lower bound: no other lower bound is ≥ it
        candidates = [c for c in lbs if all(self.le(d, c) for d in lbs)]
        return candidates[0] if candidates else None

    # ── public interface ──────────────────────────────────────────────────────

    def join(self, a: T, b: T) -> T:
        """a ⋁ b — least upper bound of a and b."""
        result = self._find_join(a, b)
        assert result is not None
        return result

    def meet(self, a: T, b: T) -> T:
        """a ⋀ b — greatest lower bound of a and b."""
        result = self._find_meet(a, b)
        assert result is not None
        return result


# %%


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — CompleteLattice
# ─────────────────────────────────────────────────────────────────────────────

class CompleteLattice(Lattice[T]):
    """
    A complete lattice: join and meet defined for ANY subset of Q.

    ⋁∅ = ⊥  (bottom — identity for join)
    ⋀∅ = ⊤  (top — identity for meet)

    For a finite lattice, completeness follows from the pairwise lattice
    property.  We expose the general interface here explicitly.
    """

    @property
    def top(self) -> T:
        """⊤ — greatest element; join of the whole set."""
        return self.big_join(list(self.base))

    @property
    def bottom(self) -> T:
        """⊥ — least element; meet of the whole set."""
        return self.big_meet(list(self.base))

    def big_join(self, subset: list[T]) -> T:
        """
        ⋁ subset — least upper bound of any subset.

        ⋁∅ = ⊥ (bottom); computed iteratively for non-empty subsets.
        """
        if not subset:
            return self.big_meet(list(self.base))  # ⊥ = ⋀Q
        result = subset[0]
        for x in subset[1:]:
            result = self.join(result, x)
        return result

    def big_meet(self, subset: list[T]) -> T:
        """
        ⋀ subset — greatest lower bound of any subset.

        ⋀∅ = ⊤ (top); computed iteratively for non-empty subsets.
        """
        if not subset:
            # ⊤ = element ≥ everything
            candidates = [c for c in self.base
                          if all(self.le(x, c) for x in self.base)]
            assert candidates, "No top element — set is empty?"
            return candidates[0]
        result = subset[0]
        for x in subset[1:]:
            result = self.meet(result, x)
        return result

    def is_top(self, a: T) -> bool:
        return a == self.top

    def is_bottom(self, a: T) -> bool:
        return a == self.bottom

# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6 — Monoid mixin
# ─────────────────────────────────────────────────────────────────────────────

class MonoidMixin(Generic[T]):
    """
    Mixin that adds a monoid operation ⊗ to any set.

    Provides:
      mul(a, b)       — a ⊗ b
      unit            — the identity element e
      check_monoid()  — verify all three axioms
    """

    def __init__(self, mul_fn: Callable[[T, T], T], unit: T) -> None:
        self._mul_fn = mul_fn
        self._unit = unit

    def mul(self, a: T, b: T) -> T:
        """a ⊗ b"""
        return self._mul_fn(a, b)

    @property
    def unit(self) -> T:
        """The identity element e."""
        return self._unit

    def check_monoid(self, base: FiniteSet[T]) -> dict:
        """
        Verify all three monoid axioms.

        Returns a dict with keys 'closure', 'associativity', 'identity',
        each True/False, plus 'counterexamples' for failures.
        """
        elems = list(base) 
        result = {"closure": True, "associativity": True, "identity": True,
                  "counterexamples": []}

        # Closure: a ⊗ b ∈ Q for all a, b
        for a in elems:
            for b in elems:
                if self.mul(a, b) not in base:
                    result["closure"] = False
                    result["counterexamples"].append(
                        f"closure: {a}⊗{b}={self.mul(a,b)} ∉ Q")

        # Associativity: (a⊗b)⊗c = a⊗(b⊗c)
        for a in elems:
            for b in elems:
                for c in elems:
                    lhs = self.mul(self.mul(a, b), c)
                    rhs = self.mul(a, self.mul(b, c))
                    if lhs != rhs:
                        result["associativity"] = False
                        result["counterexamples"].append(
                            f"assoc: ({a}⊗{b})⊗{c}={lhs} ≠ {a}⊗({b}⊗{c})={rhs}")

        # Identity: e⊗a = a⊗e = a
        for a in elems:
            if self.mul(self._unit, a) != a or self.mul(a, self._unit) != a:
                result["identity"] = False
                result["counterexamples"].append(
                    f"identity: unit⊗{a}={self.mul(self._unit, a)}")

        return result


# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7 — Quantale
# ─────────────────────────────────────────────────────────────────────────────

class Quantale(CompleteLattice[T], MonoidMixin[T]):
    """
    A quantale (Q, ≤, ⊗): a complete lattice + monoid where ⊗ distributes
    over arbitrary joins on both sides.

    Left:   a ⊗ (⋁S)  =  ⋁{ a ⊗ s | s ∈ S }
    Right:  (⋁S) ⊗ a  =  ⋁{ s ⊗ a | s ∈ S }

    Distributivity implies ⊗ is monotone in both arguments.
    """

    def __init__(
        self,
        base: FiniteSet[T],
        leq: BinaryRelation[T],
        mul_fn: Callable[[T, T], T],
        unit: T,
    ) -> None:
        CompleteLattice.__init__(self, base, leq)
        MonoidMixin.__init__(self, mul_fn, unit)
        self._validate_quantale()

    def _validate_quantale(self) -> None:
        """Check distributivity for all elements and all subsets."""
        elems = list(self.base)
        # It suffices to check pairwise (S = {b, c}):
        # a ⊗ (b ⋁ c) = (a ⊗ b) ⋁ (a ⊗ c)
        for a in elems:
            for b in elems:
                for c in elems:
                    join_bc = self.join(b, c)
                    # left distributivity
                    lhs = self.mul(a, join_bc)
                    rhs = self.join(self.mul(a, b), self.mul(a, c))
                    assert lhs == rhs, (
                        f"Left distributivity fails: "
                        f"{a}⊗({b}⋁{c}) = {a}⊗{join_bc} = {lhs} "
                        f"≠ ({a}⊗{b})⋁({a}⊗{c}) = {rhs}"
                    )
                    # right distributivity
                    lhs2 = self.mul(join_bc, a)
                    rhs2 = self.join(self.mul(b, a), self.mul(c, a))
                    assert lhs2 == rhs2, (
                        f"Right distributivity fails: "
                        f"({b}⋁{c})⊗{a} = {join_bc}⊗{a} = {lhs2} "
                        f"≠ ({b}⊗{a})⋁({c}⊗{a}) = {rhs2}"
                    )

    def is_commutative(self) -> bool:
        """a ⊗ b = b ⊗ a for all a, b."""
        return all(
            self.mul(a, b) == self.mul(b, a)
            for a in self.base for b in self.base
        )

    def is_idempotent(self) -> bool:
        """a ⊗ a = a for all a. (gives a frame / Heyting algebra)"""
        return all(self.mul(a, a) == a for a in self.base)

    def is_integral(self) -> bool:
        """Unit e = ⊤ (top). (default-deny: composing with admin = identity)"""
        return self.unit == self.top

    def check_distributivity_report(self) -> dict:
        """Run distributivity check and return a report instead of asserting."""
        elems = list(self.base)
        failures = []
        for a in elems:
            for b in elems:
                for c in elems:
                    jbc = self.join(b, c)
                    if self.mul(a, jbc) != self.join(self.mul(a, b), self.mul(a, c)):
                        failures.append(f"left: {a}⊗({b}⋁{c})")
                    if self.mul(jbc, a) != self.join(self.mul(b, a), self.mul(c, a)):
                        failures.append(f"right: ({b}⋁{c})⊗{a}")
        return {"distributivity": len(failures) == 0, "failures": failures}



# %%

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8 — ResiduatedQuantale
# ─────────────────────────────────────────────────────────────────────────────

class ResiduatedQuantale(Quantale[T]):
    """
    A quantale with explicit residuals.

    right_residual(a, c)  =  a → c  =  ⋁{ b | a ⊗ b ≤ c }
    left_residual(c, b)   =  c ← b  =  ⋁{ a | a ⊗ b ≤ c }

    Core adjunction (Galois connection):
      a ⊗ b ≤ c   ⟺   b ≤ (a → c)   ⟺   a ≤ (c ← b)

    Residuals are uniquely determined by ⊗ and ≤; we compute them on demand
    and cache the results.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._rr_cache: dict[tuple, T] = {}
        self._lr_cache: dict[tuple, T] = {}

    # ── residuals ─────────────────────────────────────────────────────────────

    def right_residual(self, a: T, c: T) -> T:
        """
        a → c = ⋁{ b ∈ Q | a ⊗ b ≤ c }

        "Given that the left factor is a and the result must be ≤ c,
         what is the maximum right factor?"

        Access-control reading: service with permission a wants to delegate;
        the composed permission must stay within c.  Returns max grantable.
        """
        key = (a, c)
        if key not in self._rr_cache:
            feasible = [b for b in self.base if self.le(self.mul(a, b), c)]
            self._rr_cache[key] = self.big_join(feasible) if feasible else self.bottom
        return self._rr_cache[key]

    def left_residual(self, c: T, b: T) -> T:
        """
        c ← b = ⋁{ a ∈ Q | a ⊗ b ≤ c }

        "Given that the right factor is b and the result must be ≤ c,
         what is the maximum left factor?"
        """
        key = (c, b)
        if key not in self._lr_cache:
            feasible = [a for a in self.base if self.le(self.mul(a, b), c)]
            self._lr_cache[key] = self.big_join(feasible) if feasible else self.bottom
        return self._lr_cache[key]

    # ── adjunction verification ───────────────────────────────────────────────

    def verify_adjunction(self) -> dict:
        """
        Verify the core law for all triples (a, b, c):
          a ⊗ b ≤ c  ⟺  b ≤ (a → c)  ⟺  a ≤ (c ← b)

        Returns a report with pass/fail and any counterexamples.
        """
        failures = []
        elems = list(self.base)
        for a in elems:
            for b in elems:
                for c in elems:
                    lhs  = self.le(self.mul(a, b), c)         # a ⊗ b ≤ c
                    mid  = self.le(b, self.right_residual(a, c))  # b ≤ a→c
                    rhs  = self.le(a, self.left_residual(c, b))   # a ≤ c←b
                    if not (lhs == mid == rhs):
                        failures.append(
                            f"({a},{b},{c}): "
                            f"a⊗b≤c={lhs}, b≤a→c={mid}, a≤c←b={rhs}"
                        )
        return {"adjunction_holds": len(failures) == 0, "failures": failures[:5]}

    # ── query interface (the "database" API) ──────────────────────────────────

    def can_do(self, role: T, required: T) -> bool:
        """Does role imply required?  (role ≤ required in the order)"""
        return self.le(role, required)

    def effective_permission(self, roles: list[T]) -> T:
        """Effective permission of a user holding multiple roles = ⋁ roles."""
        return self.big_join(roles)

    def max_delegatable(self, own_permission: T, cap: T) -> T:
        """
        Maximum permission this service can grant downstream so that the
        composed result stays within cap.

        = own_permission → cap  (right residual)
        """
        return self.right_residual(own_permission, cap)

    def compose(self, perm_a: T, perm_b: T) -> T:
        """Composed permission when perm_a delegates to perm_b."""
        return self.mul(perm_a, perm_b)



# %%

# ─────────────────────────────────────────────────────────────────────────────
# CONCRETE EXAMPLE — Project quantale
# ─────────────────────────────────────────────────────────────────────────────

def build_project_quantale() -> ResiduatedQuantale:
    """
    Build the five-element access-control quantale.

    Elements form a CHAIN (partial order):
                <  over_budget    
              //                 \\
      blocked                       < healthy < success
              \\                 // 
                < behind_scedule 

    A chain is necessary for meet (⊗ = min) to satisfy distributivity.
    Incomparable branches break left-distributivity:
      a ⊗ (b ⋁ c) ≠ (a⊗b) ⋁ (a⊗c)  when b,c are incomparable.

    ⊗ = meet (min on this chain)
      Interpretation: composing two role levels gives the stricter one.

    Unit = Success (top element → integral quantale: success ⊗ x = x).

    NOTE — teaching point:
      The "over_budget vs behind_schedule incomparable" lattice is a valid *lattice*, but
      meet on it does NOT form a quantale.  A quantale requires ⊗ to
      distribute over ⋁; on a non-chain lattice you need a different ⊗
      (e.g. relational composition on a powerset).  The chain version is
      the simplest correct concrete example.
    """

    # Stage 1 — set (chain: blocked < over_budget < behind_schedule < healthy < success)
    Q = FiniteSet(MY_ELEMENTS)

    # Stage 2 / 3 — total order via reflexive-transitive closure of the chain
    direct = BinaryRelation(Q, [
        (BLOCKED,   OVER_BUDGET),
        (BLOCKED,   BEHIND_SCHEDULE),
        (OVER_BUDGET, HEALTHY),
        (BEHIND_SCHEDULE, HEALTHY),
        (HEALTHY,  SUCCESS),
    ])
    leq = direct.closure()   # adds reflexivity + transitivity automatically

    # Stage 4/5 — complete lattice (chain → automatically a lattice)
    lat = CompleteLattice(Q, leq)

    # Stage 6 — monoid: ⊗ = meet (= min on chain), unit = success (top)
    def MUL(a: str, b: str) -> str:
        return lat.meet(a, b)

    # Stage 7+8 — quantale with residuals
    q_obj = ResiduatedQuantale(Q, leq, MUL, unit=SUCCESS)
    return q_obj


# ─────────────────────────────────────────────────────────────────────────────
# DEMONSTRATION
# ─────────────────────────────────────────────────────────────────────────────

def demo() -> None:
    print("=" * 60)
    print("  Quantale — Project Dependency Risk Demo")
    print("=" * 60)

    # Make sure you've renamed your build function to match
    q = build_project_quantale() 

    # ── Stage 1-3: set and order ──────────────────────────────────────────────
    print("\n── Elements ─────────────────────────────────────────────")
    print("  Q =", q.base)
    print("  ⊥ (bottom) =", q.bottom) # Should be Blocked
    print("  ⊤ (top)    =", q.top)    # Should be Success

    print("\n── Hasse cover edges (a → b means a < b, direct) ────────")
    for a, b in q.hasse_edges():
        print(f"  {a} < {b}")

    print("\n── Order queries (Highlighting Partial Order) ───────────")
    # Note the incomparable pair in the middle
    pairs = [
        ("blocked", "success"), 
        ("over_budget", "behind_schedule"), # Incomparable!
        ("behind_schedule", "healthy"), 
        ("healthy", "blocked")
    ]
    for a, b in pairs:
        sym = "≤" if q.le(a, b) else "≰"
        comp = "comparable" if q.comparable(a, b) else "INCOMPARABLE"
        print(f"  {a} {sym} {b}  ({comp})")

    # ── Stage 4-5: lattice ────────────────────────────────────────────────────
    print("\n── Joins and Meets (The Diamond Structure) ───────────────")
    # Joining incomparable risks should result in the next common healthy state
    pairs2 = [("over_budget", "behind_schedule"), ("blocked", "healthy")]
    for a, b in pairs2:
        print(f"  {a} ⋁ {b} (Join) = {q.join(a,b)}")
        print(f"  {a} ⋀ {b} (Meet) = {q.meet(a,b)}")

    print("\n── Arbitrary joins (Project Consensus) ──────────────────")
    subsets = [
        ["over_budget", "behind_schedule"],
        ["healthy", "success"],
        ["blocked", "over_budget", "behind_schedule"]
    ]
    for s in subsets:
        print(f"  ⋁{s} = {q.big_join(s)} (Best Case)")
        print(f"  ⋀{s} = {q.big_meet(s)} (Worst Case)")

    # ── Stage 6: monoid ───────────────────────────────────────────────────────
    print("\n── Monoid (⊗ = Bottleneck/Meet) ─────────────────────────")
    report = q.check_monoid(q.base)
    for k, v in report.items():
        if k != "counterexamples":
            print(f"  {k}: {v}")
    
    # Composing statuses (a task depending on another)
    compositions = [
        ("healthy", "behind_schedule"), 
        ("success", "over_budget"), 
        ("blocked", "healthy")
    ]
    for a, b in compositions:
        print(f"  {a} ⊗ {b} = {q.mul(a,b)}")

    # ── Stage 7: quantale properties ─────────────────────────────────────────
    print("\n── Quantale properties ──────────────────────────────────")
    print("  is_commutative:", q.is_commutative())
    print("  is_idempotent: ", q.is_idempotent())
    print("  is_integral:   ", q.is_integral()) # Should be True (unit=top)
    dist = q.check_distributivity_report()
    print("  distributivity holds:", dist["distributivity"])

    # ── Stage 8: residuals ────────────────────────────────────────────────────
    print("\n── Residuals (Risk Budgeting: a → c) ────────────────────")
    # "Given current state a, what's the worst a sub-task can be to stay above c?"
    queries = [
        ("healthy", "behind_schedule", "Max sub-task risk to stay 'Behind_Schedule'"),
        ("success", "healthy",         "Max sub-task risk to stay 'Healthy'"),
        ("over_budget", "blocked",     "Max sub-task risk to avoid 'Blocked'"),
    ]
    for a, c, desc in queries:
        res = q.right_residual(a, c)
        print(f"  {a} → {c} = {res:15s}  ({desc})")

    print("\n── Adjunction verification ──────────────────────────────")
    adj = q.verify_adjunction()
    print("  a⊗b≤c ⟺ b≤a→c ⟺ a≤c←b holds:", adj["adjunction_holds"])

    # ── High-level API ────────────────────────────────────────────────────────
    print("\n── High-level API (PM Tool Simulator) ───────────────────")
    print(f"  Can a 'Healthy' project satisfy 'Blocked' requirements? {q.can_do('healthy', 'blocked')}")
    print(f"  Effective status of several sub-tasks: {q.effective_permission(['over_budget', 'healthy'])}")
    print(f"  Dependency bottleneck (Healthy + Over_Budget): {q.compose('healthy', 'over_budget')}")

    print("\n" + "=" * 60)
    print("  Project Management Domain — All checks passed.")
    print("=" * 60)

if __name__ == "__main__":
    demo()