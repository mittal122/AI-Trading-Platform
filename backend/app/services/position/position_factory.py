from backend.app.services.position.fixed_position import (
    FixedPosition,
)


class PositionFactory:

    @staticmethod
    def get_engine(
        name: str = "fixed",
    ):

        engines = {
            "fixed": FixedPosition,
        }

        name = name.lower()

        if name not in engines:
            raise ValueError(
                f"Unknown position engine: {name}"
            )

        return engines[name]()