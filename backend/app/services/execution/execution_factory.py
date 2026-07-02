from backend.app.services.execution.simple_execution import SimpleExecution


class ExecutionFactory:

    @staticmethod
    def get_engine(name: str = "simple"):
        name = name.lower()
        if name == "simple":
            return SimpleExecution()
        raise ValueError(f"Unknown execution engine: {name}. Use ExecutionFactory or BinanceExecution directly.")