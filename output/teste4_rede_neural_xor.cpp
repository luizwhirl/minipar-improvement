#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <memory>
#include <cstring>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <type_traits>

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

auto sigmoid(auto x) {
    return (1 / (1 + std::exp((0 - x))));
}

auto derivada_sigmoid(auto saida) {
    return (saida * (1 - saida));
}

class RedeNeuralXOR {
public:
    decltype(0.5) taxa_aprendizado = 0.5;
    decltype(0.2) h1_w1 = 0.2;
    decltype((-0.4)) h1_w2 = (-0.4);
    decltype(0.0) h1_bias = 0.0;
    decltype((-0.3)) h2_w1 = (-0.3);
    decltype(0.6) h2_w2 = 0.6;
    decltype(0.1) h2_bias = 0.1;
    decltype(0.7) h3_w1 = 0.7;
    decltype(0.5) h3_w2 = 0.5;
    decltype((-0.2)) h3_bias = (-0.2);
    decltype(0.4) out_w1 = 0.4;
    decltype((-0.5)) out_w2 = (-0.5);
    decltype(0.3) out_w3 = 0.3;
    decltype(0.0) out_bias = 0.0;
    decltype(0.0) h1 = 0.0;
    decltype(0.0) h2 = 0.0;
    decltype(0.0) h3 = 0.0;
    decltype(0.0) saida = 0.0;
    auto feedforward(auto x1, auto x2) {
        this->h1 = sigmoid((((x1 * this->h1_w1) + (x2 * this->h1_w2)) + this->h1_bias));
        this->h2 = sigmoid((((x1 * this->h2_w1) + (x2 * this->h2_w2)) + this->h2_bias));
        this->h3 = sigmoid((((x1 * this->h3_w1) + (x2 * this->h3_w2)) + this->h3_bias));
        this->saida = sigmoid(((((this->h1 * this->out_w1) + (this->h2 * this->out_w2)) + (this->h3 * this->out_w3)) + this->out_bias));
        return this->saida;
    }
    void treinar_amostra(auto x1, auto x2, auto desejado) {
        auto previsto = this->feedforward(x1, x2);
        auto erro = (desejado - previsto);
        auto delta_saida = (erro * derivada_sigmoid(previsto));
        auto antigo_out_w1 = this->out_w1;
        auto antigo_out_w2 = this->out_w2;
        auto antigo_out_w3 = this->out_w3;
        this->out_w1 = (this->out_w1 + ((this->h1 * delta_saida) * this->taxa_aprendizado));
        this->out_w2 = (this->out_w2 + ((this->h2 * delta_saida) * this->taxa_aprendizado));
        this->out_w3 = (this->out_w3 + ((this->h3 * delta_saida) * this->taxa_aprendizado));
        this->out_bias = (this->out_bias + (delta_saida * this->taxa_aprendizado));
        auto delta_h1 = ((delta_saida * antigo_out_w1) * derivada_sigmoid(this->h1));
        auto delta_h2 = ((delta_saida * antigo_out_w2) * derivada_sigmoid(this->h2));
        auto delta_h3 = ((delta_saida * antigo_out_w3) * derivada_sigmoid(this->h3));
        this->h1_w1 = (this->h1_w1 + ((x1 * delta_h1) * this->taxa_aprendizado));
        this->h1_w2 = (this->h1_w2 + ((x2 * delta_h1) * this->taxa_aprendizado));
        this->h1_bias = (this->h1_bias + (delta_h1 * this->taxa_aprendizado));
        this->h2_w1 = (this->h2_w1 + ((x1 * delta_h2) * this->taxa_aprendizado));
        this->h2_w2 = (this->h2_w2 + ((x2 * delta_h2) * this->taxa_aprendizado));
        this->h2_bias = (this->h2_bias + (delta_h2 * this->taxa_aprendizado));
        this->h3_w1 = (this->h3_w1 + ((x1 * delta_h3) * this->taxa_aprendizado));
        this->h3_w2 = (this->h3_w2 + ((x2 * delta_h3) * this->taxa_aprendizado));
        this->h3_bias = (this->h3_bias + (delta_h3 * this->taxa_aprendizado));
    }
    void treinar() {
        auto epoca = 0;
        while ((epoca < 20000))
        {
            this->treinar_amostra(0, 0, 0);
            this->treinar_amostra(0, 1, 1);
            this->treinar_amostra(1, 0, 1);
            this->treinar_amostra(1, 1, 0);
            epoca = (epoca + 1);
        }
    }
    void testar() {
        std::cout << "==== Teste 4: rede neural XOR com backpropagation ====" << std::endl;
        std::cout << "Input: [0, 0], Predicted Output:" << " " << this->feedforward(0, 0) << std::endl;
        std::cout << "Input: [0, 1], Predicted Output:" << " " << this->feedforward(0, 1) << std::endl;
        std::cout << "Input: [1, 0], Predicted Output:" << " " << this->feedforward(1, 0) << std::endl;
        std::cout << "Input: [1, 1], Predicted Output:" << " " << this->feedforward(1, 1) << std::endl;
    }
};

int main() {
    #ifdef _WIN32
        WSADATA wsa;
        WSAStartup(MAKEWORD(2,2), &wsa);
    #endif

    auto rede = std::make_shared<RedeNeuralXOR>();
    rede->treinar();
    rede->testar();

    return 0;
}
