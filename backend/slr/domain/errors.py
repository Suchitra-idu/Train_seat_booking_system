"""Domain error family. L4 maps these to HTTP (Overlap→409, cap→429, invalid→422)."""

from __future__ import annotations


class DomainError(Exception):
    """Base for every rule violation the pure core can raise."""


class InvalidLeg(DomainError):
    """A leg that is empty, reversed, or off the station sequence."""


class IllegalTransition(DomainError):
    """A booking status change the state machine forbids."""


class NoFeasibleSeat(DomainError):
    """No seat can hold this leg without overlapping an existing occupancy."""
