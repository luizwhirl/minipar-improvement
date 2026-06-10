CXX = g++
CXXFLAGS = -Wall -std=c++17 -I./src
SRCS = src/main.cpp src/lexer.cpp src/parser.cpp src/semantic.cpp src/codegen.cpp
OBJS = $(SRCS:.cpp=.o)
TARGET = minipar_compiler.exe

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)
	@echo "Compilador MiniPar construído com sucesso!"

clean:
	rm -f src/*.o $(TARGET) output/*.cpp output/*.exe