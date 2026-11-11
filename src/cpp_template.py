_CPP_HEADER = """\
#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <thread>
#include <memory>
#include <cstring>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <type_traits>
#include <future>
#include <mutex>
#include <deque>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  #define CLOSE_SOCK closesocket
#else
  #include <sys/socket.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #define CLOSE_SOCK close
#endif

// ===== fork / join =====
// Cada fork vira uma tarefa (std::async, uma thread do sistema) guardada numa
// lista global. O fork devolve o numero da tarefa (um double), entao ele pode ir
// para variaveis e listas como qualquer numero. O join espera a tarefa e devolve o resultado.
static std::deque<std::shared_future<double>> __tasks;
static std::mutex __tasks_mtx;

template <class F>
double __as_double(F&& fn) {
    if constexpr (std::is_void_v<decltype(fn())>) { fn(); return 0.0; }
    else return static_cast<double>(fn());
}

template <class F>
double __fork(F fn) {
    auto fut = std::async(std::launch::async, [fn]() mutable { return __as_double(fn); }).share();
    std::lock_guard<std::mutex> lock(__tasks_mtx);
    __tasks.push_back(fut);
    return static_cast<double>(__tasks.size() - 1);
}

inline double __join(double id) {
    std::shared_future<double> fut;
    {
        std::lock_guard<std::mutex> lock(__tasks_mtx);
        size_t i = static_cast<size_t>(id);
        if (id < 0 || i >= __tasks.size()) {
            std::cerr << "[ERRO EXECUCAO] join em tarefa inexistente: " << id << std::endl;
            std::exit(1);
        }
        fut = __tasks[i];
    }
    return fut.get();
}

// Helper para Random nativo
double random_val() { return (double)rand() / RAND_MAX; }

// Helper para Input
std::string input() {
    std::string s;
    std::getline(std::cin, s);
    return s;
}

std::string input(const std::string& prompt) {
    std::cout << prompt;
    return input();
}

// Converte linha com inteiros separados por espaco em vetor (ex.: "10 -3 80")
std::vector<double> __parse_ints(const std::string& s) {
    std::vector<double> result;
    std::istringstream iss(s);
    double n;
    while (iss >> n) {
        result.push_back(n);
    }
    return result;
}

std::vector<int> __minipar_range(int end) {
    std::vector<int> values;
    for (int i = 0; i < end; ++i) values.push_back(i);
    return values;
}

std::vector<int> __minipar_range(int start, int end) {
    std::vector<int> values;
    for (int i = start; i < end; ++i) values.push_back(i);
    return values;
}

// Helper para Arrays (.pop) do Python
template<typename T>
auto __array_pop(std::vector<T>& v) {
    if (v.empty()) return T{};
    auto val = v.back();
    v.pop_back();
    return val;
}

// Helper para formatar e printar std::vector (arrays e matrizes) nativamente
template <typename T>
std::ostream& operator<<(std::ostream& os, const std::vector<T>& v) {
    os << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        os << v[i];
        if (i != v.size() - 1) os << ", ";
    }
    os << "]";
    return os;
}

template<typename T>
std::string __to_string(const T& val) {
    if constexpr (std::is_constructible_v<std::string, T>) {
        return std::string(val);
    } else {
        return std::to_string(val);
    }
}

// ===== funcoes de texto =====
// to_string(x): numero (ou texto) vira texto, no mesmo formato do print (42 e nao 42.000000).
template<typename T>
std::string __minipar_to_string(const T& val) {
    std::ostringstream os;
    os << val;
    return os.str();
}

// substr(s, inicio, tamanho): pedaco do texto; se passar do fim, corta ate o fim.
inline std::string __substr(const std::string& s, double inicio, double tamanho) {
    if (inicio < 0 || inicio > static_cast<double>(s.size())) {
        std::cerr << "[ERRO EXECUCAO] substr com inicio fora do texto: " << inicio << std::endl;
        std::exit(1);
    }
    if (tamanho < 0) tamanho = 0;
    return s.substr(static_cast<size_t>(inicio), static_cast<size_t>(tamanho));
}

// s[i] e lista[i]: em texto devolve o caractere i como texto de 1 letra
// (para comparar com "a"); em lista e matriz continua sendo o v[i] de sempre
// (pode receber valor: lista[i] = 5).
template<typename V, typename I>
decltype(auto) __index(V&& v, I i) {
    if constexpr (std::is_same_v<std::decay_t<V>, std::string>) {
        if (i < 0 || static_cast<size_t>(i) >= v.size()) {
            std::cerr << "[ERRO EXECUCAO] indice fora do texto: " << i << std::endl;
            std::exit(1);
        }
        return std::string(1, v[static_cast<size_t>(i)]);
    } else {
        return std::forward<V>(v)[static_cast<size_t>(i)];
    }
}

template<typename T>
auto __make_matrix(int rows, int cols, T init_val) {
    using ActualT = std::conditional_t<std::is_same_v<std::decay_t<T>, const char*>, std::string, T>;
    return std::vector<std::vector<ActualT>>(rows, std::vector<ActualT>(cols, init_val));
}

class MiniParChannel {
public:
    std::string ip;
    int port;

    MiniParChannel(std::string ip, int port) : ip(ip), port(port) {}

    void sendData(std::string msg) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) return;
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &serv_addr.sin_addr);
        
        for(int i=0; i<50; i++) {
            if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                send(sock, msg.c_str(), msg.length(), 0);
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        CLOSE_SOCK(sock);
    }

    std::string receiveData() {
        int server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd < 0) return "";
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
        
        struct sockaddr_in address;
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);
        
        if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) < 0) { CLOSE_SOCK(server_fd); return ""; }
        if (listen(server_fd, 3) < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        int new_socket = accept(server_fd, nullptr, nullptr);
        if (new_socket < 0) { CLOSE_SOCK(server_fd); return ""; }
        
        char buffer[4096] = {0};
        recv(new_socket, buffer, 4096, 0);
        std::string result(buffer);
        
        CLOSE_SOCK(new_socket);
        CLOSE_SOCK(server_fd);
        return result;
    }
};

"""
