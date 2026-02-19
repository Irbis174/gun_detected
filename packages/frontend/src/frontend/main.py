from ml.main import zeros, cuda
#from backend.main import hello
from backend import hello

def hello_frontend():
    return "Hello from Frontend"


if __name__ == "__main__":
    print(zeros())
    print(hello())
    print(cuda())