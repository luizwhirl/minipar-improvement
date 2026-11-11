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
#include <stdexcept>
#include <algorithm>
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

// Encerra o programa na hora com erro. Usa _Exit porque std::exit esperaria
// as outras tarefas (std::async) terminarem, e uma tarefa travada travaria tudo.
[[noreturn]] inline void __fail_now(const std::string& msg) {
    std::cout.flush();
    std::cerr << "[ERRO EXECUCAO] " << msg << std::endl;
    std::cerr.flush();
    std::_Exit(1);
}

// join(t, ms): espera no maximo ms milissegundos (ms < 0 = sem limite).
inline double __join(double id, double timeout_ms) {
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
    if (timeout_ms >= 0) {
        auto limit = std::chrono::milliseconds(static_cast<long long>(timeout_ms));
        if (fut.wait_for(limit) != std::future_status::ready) {
            std::ostringstream msg;
            msg << "join: a tarefa " << id << " passou do tempo limite de " << timeout_ms << " ms.";
            __fail_now(msg.str());
        }
    }
    try {
        return fut.get();
    } catch (const std::exception& e) {
        __fail_now(std::string("join: a tarefa ") + std::to_string(static_cast<long long>(id)) + " falhou: " + e.what());
    }
}

// join(t): espera o tempo que for preciso.
inline double __join(double id) { return __join(id, -1); }

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
    } else if constexpr (std::is_arithmetic_v<T>) {
        return std::to_string(val);
    } else {
        std::ostringstream text;
        text << val;
        return text.str();
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

private:
    int listener = -1;
    std::mutex receiving;

public:

    MiniParChannel(std::string ip, int port) : ip(ip), port(port) {}

    ~MiniParChannel() {
        if (listener >= 0) CLOSE_SOCK(listener);
    }

    void sendData(std::string msg) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) throw std::runtime_error("Falha ao abrir o canal de envio.");
        struct sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip.c_str(), &serv_addr.sin_addr);
        
        bool connected = false;
        for(int i=0; i<50; i++) {
            if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) >= 0) {
                connected = true;
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if (!connected) {
            CLOSE_SOCK(sock);
            throw std::runtime_error("Nao foi possivel conectar ao canal de comunicacao.");
        }
        size_t offset = 0;
        while (offset < msg.size()) {
            int count = send(sock, msg.data() + offset,
                static_cast<int>(std::min(msg.size() - offset, size_t(4096))), 0);
            if (count <= 0) {
                CLOSE_SOCK(sock);
                throw std::runtime_error("Falha ao enviar a mensagem completa pelo canal.");
            }
            offset += count;
        }
        // Closing the sending connection frames one complete message, as in
        // the original channel protocol, including an empty string.
        CLOSE_SOCK(sock);
    }

    std::string receiveData() {
        std::lock_guard<std::mutex> lock(receiving);
        // One listener belongs to the channel for its entire lifetime. Closing
        // and recreating it on every receive could discard connections queued
        // for the following message while the previous message was consumed.
        if (listener < 0) {
            listener = socket(AF_INET, SOCK_STREAM, 0);
            if (listener < 0) throw std::runtime_error("Falha ao abrir o canal de recepcao.");
            int opt = 1;
            setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
            struct sockaddr_in address;
            address.sin_family = AF_INET;
            address.sin_addr.s_addr = INADDR_ANY;
            address.sin_port = htons(port);
            if (bind(listener, (struct sockaddr*)&address, sizeof(address)) < 0
                    || listen(listener, SOMAXCONN) < 0) {
                CLOSE_SOCK(listener);
                listener = -1;
                throw std::runtime_error("Nao foi possivel escutar na porta do canal.");
            }
        }
        int new_socket = accept(listener, nullptr, nullptr);
        if (new_socket < 0) throw std::runtime_error("Falha ao aceitar a conexao do canal.");
        
        char buffer[4096];
        std::string result;
        int count;
        while ((count = recv(new_socket, buffer, sizeof(buffer), 0)) > 0) {
            result.append(buffer, count);
        }
        if (count < 0) {
            CLOSE_SOCK(new_socket);
            throw std::runtime_error("Falha ao receber a mensagem completa pelo canal.");
        }
        CLOSE_SOCK(new_socket);
        return result;
    }
};

"""
