"""Domain error family. L4 maps these to HTTP (Overlap→409, cap→429, invalid→422)."""

from __future__ import annotations


class DomainError(Exception):
    """Base for every rule violation the pure core can raise."""


class InvalidLeg(DomainError):
    """A leg that is empty, reversed, or off the station sequence."""


class InvalidServiceDate(DomainError):
    """A malformed date/time, or one outside the bookable window (D22). Maps to 422."""


class IllegalTransition(DomainError):
    """A booking status change the state machine forbids."""


class NoFeasibleSeat(DomainError):
    """No seat can hold this leg without overlapping an existing occupancy."""


class OverlapError(DomainError):
    """A seat/leg is already held by an active booking (D2). Maps to 409."""


class AntiAbuseError(DomainError):
    """An intent blocked by anti-tout policy (D9). Maps to 429."""


class SeatCapExceeded(AntiAbuseError):
    """The passenger already holds the per-trip seat cap."""


class VelocityExceeded(AntiAbuseError):
    """Too many bookings from one actor inside the velocity window."""


class AbuseSuspected(AntiAbuseError):
    """The risk score crossed the configured cut-off."""


class PaymentDeclined(DomainError):
    """The gateway rejected the charge. Maps to 402."""


class CoachFull(DomainError):
    """Unreserved standing capacity is exhausted, no seat and no standing room."""


class BookingNotFound(DomainError):
    """No booking matches the reference or id. Maps to 404."""


class SeatNotBookable(DomainError):
    """The chosen seat does not exist or is not individually reservable. Maps to 422."""
