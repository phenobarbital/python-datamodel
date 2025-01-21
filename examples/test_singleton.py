from datamodel.typedefs.singleton import Singleton
# Example classes using the Singleton metaclass

class DatabaseConnection(metaclass=Singleton):
    def __init__(self, db_name):
        print(f"Connecting to database: {db_name}")
        self.db_name = db_name

    def query(self, sql):
        print(f"Executing query on {self.db_name}: {sql}")


class Logger(metaclass=Singleton):
    def __init__(self, log_file):
        print('CALLING INIT')
        print(f"Opening log file: {log_file}")
        self.log_file = log_file

    def log(self, message):
        print(f"Logging to {self.log_file}: {message}")


# Test the Singleton behavior
if __name__ == "__main__":
    # Test with DatabaseConnection
    db1 = DatabaseConnection("mydatabase")
    db2 = DatabaseConnection("anotherdatabase")  # Should be the same instance as db1

    print(f"db1 is db2: {db1 is db2}")  # Expected: True

    # Test that a second instance can be created
    db3 = DatabaseConnection("thirddatabase")
    print(f"db1 is db3: {db1 is db3}")  # Expected: True

    # Test with Logger
    log1 = Logger("app.log")
    log2 = Logger("debug.log")  # Should be the same instance as log1

    print(f"log1 is log2: {log1 is log2}")  # Expected: True

    # Test that a second instance cannot be created, will be the same instance as log
    log3 = Logger("third.log")
    print(f"log1 is log3: {log1 is log3}")  # Expected: True
    print(f"log2 is log3: {log2 is log3}")  # Expected: True
    print('Expected : ', log1.log_file == log2.log_file == log3.log_file)  # Expected: True
