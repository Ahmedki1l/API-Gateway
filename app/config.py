from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQL Server
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_server: str = "localhost"
    db_port: int = 1433
    db_name: str = "ParkingDB"
    db_user: str = "sa"
    db_password: str = ""
    db_trusted_connection: bool = False

    # Upstream systems
    system1_base_url: str = "http://localhost:8080"
    system2_base_url: str = "http://localhost:8000"

    # Gateway
    gateway_port: int = 8001
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def db_connection_string(self) -> str:
        driver = self.db_driver.replace(" ", "+")
        if self.db_trusted_connection:
            return (
                f"mssql+pyodbc://{self.db_server}/{self.db_name}"
                f"?driver={driver}&trusted_connection=yes"
            )
        return (
            f"mssql+pyodbc://{self.db_user}:{self.db_password}"
            f"@{self.db_server}/{self.db_name}"
            f"?driver={driver}"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
