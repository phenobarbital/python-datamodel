import cProfile
from datamodel import Model

class User(Model):
    name: str
    age: int

def main():
    user = User(name='John', age=18)
    print(user)

if __name__ == "__main__":
    # Run cProfile and save the profiling results to a file
    cProfile.run("main()", filename="profile_results.prof")
