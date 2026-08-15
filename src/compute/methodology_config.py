"""Version-controlled settings for OPM prediction methodologies."""

ACTIVE_METHODOLOGY = "main_last_4"
LAST_8_RECENT_SHARE = 0.70
LAST_8_OLDER_SHARE = 0.30


class MethodologyConfigurationError(ValueError):
    """Raised when a methodology setting is not internally consistent."""


def validate_methodology_configuration(
    active_methodology=ACTIVE_METHODOLOGY,
    recent_share=LAST_8_RECENT_SHARE,
    older_share=LAST_8_OLDER_SHARE,
):
    if active_methodology not in {"main_last_4", "last_8"}:
        raise MethodologyConfigurationError(
            f"Unsupported active methodology: {active_methodology}"
        )

    try:
        recent_share = float(recent_share)
        older_share = float(older_share)
    except (TypeError, ValueError) as error:
        raise MethodologyConfigurationError(
            "Last-8 weight shares must be numeric."
        ) from error

    if not 0 <= recent_share <= 1 or not 0 <= older_share <= 1:
        raise MethodologyConfigurationError(
            "Last-8 weight shares must be between 0 and 1."
        )
    if abs((recent_share + older_share) - 1.0) > 1e-9:
        raise MethodologyConfigurationError(
            "Last-8 recent and older shares must sum to 1."
        )

    return {
        "active_methodology": active_methodology,
        "recent_share": recent_share,
        "older_share": older_share,
    }
