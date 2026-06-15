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

auto relu(auto x) {
    if ((x > 0))
    {
        return x;
    }
    return 0.0;
}

auto sigmoid(auto x) {
    return (1 / (1 + std::exp((0 - x))));
}

auto peso_entrada_oculta(auto produto, auto neuronio) {
    auto base = (((produto + 1) * (neuronio + 2)) % 7);
    return ((base + 1) / 20.0);
}

auto bias_oculto(auto neuronio) {
    return ((neuronio % 3) / 20.0);
}

auto peso_oculta_saida(auto neuronio, auto produto) {
    auto base = (((neuronio + 3) * (produto + 1)) % 5);
    return ((base + 1) / 25.0);
}

auto bias_saida(auto produto, auto historico) {
    if ((historico[produto] == 1))
    {
        return (-0.25);
    }
    return (-0.10);
}

auto nome_produto(auto indice) {
    if ((indice == 0))
    {
        return "Smartphone";
    }
    if ((indice == 1))
    {
        return "Laptop";
    }
    if ((indice == 2))
    {
        return "Tablet";
    }
    if ((indice == 3))
    {
        return "Fones de ouvido";
    }
    if ((indice == 4))
    {
        return "Camisa";
    }
    if ((indice == 5))
    {
        return "Jeans";
    }
    if ((indice == 6))
    {
        return "Jaqueta";
    }
    if ((indice == 7))
    {
        return "Sapatos";
    }
    if ((indice == 8))
    {
        return "Geladeira";
    }
    if ((indice == 9))
    {
        return "Micro-ondas";
    }
    if ((indice == 10))
    {
        return "Maquina de lavar";
    }
    if ((indice == 11))
    {
        return "Ar condicionado";
    }
    if ((indice == 12))
    {
        return "Ficcao";
    }
    if ((indice == 13))
    {
        return "Nao-ficcao";
    }
    if ((indice == 14))
    {
        return "Ficcao cientifica";
    }
    return "Fantasia";
}

class Usuario {
public:
    auto codificar_historico() {
        return std::vector<double>{1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0};
    }
};

class RedeNeuralRecomendacao {
public:
    decltype(16) input_size = 16;
    decltype(10) hidden_size = 10;
    decltype(16) output_size = 16;
    auto forward(auto historico) {
        auto ocultas = std::vector<double>{0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        auto saidas = std::vector<double>{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        auto h = 0;
        while ((h < this->hidden_size))
        {
            auto soma_oculta = 0.0;
            auto entrada = 0;
            while ((entrada < this->input_size))
            {
                soma_oculta = (soma_oculta + (historico[entrada] * peso_entrada_oculta(entrada, h)));
                entrada = (entrada + 1);
            }
            ocultas[h] = relu((soma_oculta + bias_oculto(h)));
            h = (h + 1);
        }
        auto produto = 0;
        while ((produto < this->output_size))
        {
            auto soma_saida = 0.0;
            auto neuronio = 0;
            while ((neuronio < this->hidden_size))
            {
                soma_saida = (soma_saida + (ocultas[neuronio] * peso_oculta_saida(neuronio, produto)));
                neuronio = (neuronio + 1);
            }
            saidas[produto] = sigmoid((soma_saida + bias_saida(produto, historico)));
            produto = (produto + 1);
        }
        return saidas;
    }
};

class Recomendador {
public:
    void recomendar() {
        auto usuario = std::make_shared<Usuario>();
        auto rede = std::make_shared<RedeNeuralRecomendacao>();
        auto historico = usuario->codificar_historico();
        auto probabilidades = rede->forward(historico);
        std::cout << "==== Teste 5: recomendacao e-commerce com rede neural ====" << std::endl;
        std::cout << "Produtos recomendados para voce:" << std::endl;
        auto produto = 0;
        while ((produto < 16))
        {
            if (((historico[produto] == 0) && (probabilidades[produto] > 0.55)))
            {
                std::cout << nome_produto(produto) << " " << "probabilidade:" << " " << probabilidades[produto] << std::endl;
            }
            produto = (produto + 1);
        }
    }
};

int main() {
    #ifdef _WIN32
        WSADATA wsa;
        WSAStartup(MAKEWORD(2,2), &wsa);
    #endif

    auto recomendador = std::make_shared<Recomendador>();
    recomendador->recomendar();

    return 0;
}
