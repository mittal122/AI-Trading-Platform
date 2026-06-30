from backend.app.services.execution.simple_execution import (
    SimpleExecution,
)


class ExecutionFactory:

    @staticmethod
    def get_engine(
        name: str = "simple",
    ):

        engines = {
            "simple": SimpleExecution,
        }

        name = name.lower()

        if name not in engines:

            raise ValueError(
                f"Unknown execution engine: {name}"
            )

        return engines[name]()