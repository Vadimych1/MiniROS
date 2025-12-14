from src.base import run_tests
from src.connections import AuthTest, PostTest, AnonTest

run_tests([
    AuthTest(),
    PostTest(),
    AnonTest()
])