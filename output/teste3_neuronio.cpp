#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <memory>
#include <cstring>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <variant>
#include <type_traits>
#include <functional>

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

// =====================================================================
// MiniParAny: tipo universal que suporta double, string, vector e matrix
// Permite passar matrizes e arrays como parametros e retorno de funcoes
// =====================================================================
struct MiniParAny;
using MiniParVec = std::vector<MiniParAny>;
using MiniParMat = std::vector<std::vector<MiniParAny>>;

struct MiniParAny {
    enum class Kind { NUM, STR, VEC, MAT, BOOL } kind = Kind::NUM;
    double num_val = 0.0;
    std::string str_val;
    MiniParVec vec_val;
    MiniParMat mat_val;

    // Construtores implicitos para conversao automatica
    MiniParAny() : kind(Kind::NUM), num_val(0.0) {}
    MiniParAny(double v) : kind(Kind::NUM), num_val(v) {}
    MiniParAny(int v) : kind(Kind::NUM), num_val((double)v) {}
    MiniParAny(bool v) : kind(Kind::BOOL), num_val(v ? 1.0 : 0.0) {}
    MiniParAny(const char* v) : kind(Kind::STR), str_val(v) {}
    MiniParAny(const std::string& v) : kind(Kind::STR), str_val(v) {}
    MiniParAny(const MiniParVec& v) : kind(Kind::VEC), vec_val(v) {}
    MiniParAny(const MiniParMat& v) : kind(Kind::MAT), mat_val(v) {}

    // Conversoes implicitas de saida
    operator double() const { 
        if (kind == Kind::STR) { try { return std::stod(str_val); } catch(...) { return 0.0; } }
        return num_val; 
    }
    operator bool() const { return num_val != 0.0 || kind == Kind::BOOL; }
    operator std::string() const { 
        if (kind == Kind::STR) return str_val;
        if (kind == Kind::NUM) {
            if (num_val == (long long)num_val) return std::to_string((long long)num_val);
            return std::to_string(num_val);
        }
        return "";
    }

    // Acesso por indice (arrays e matrizes)
    MiniParAny& operator[](int idx) {
        if (kind == Kind::VEC) return vec_val[idx];
        if (kind == Kind::MAT) { static MiniParAny dummy; return dummy; }
        return *this;
    }
    const MiniParAny& operator[](int idx) const {
        if (kind == Kind::VEC) return vec_val[idx];
        return *this;
    }
    // Acesso a linha de matriz (retorna o vetor da linha)
    MiniParVec& mat_row(int idx) { return mat_val[idx]; }

    // size() para arrays e matrizes
    std::size_t size() const {
        if (kind == Kind::VEC) return vec_val.size();
        if (kind == Kind::MAT) return mat_val.size();
        return 0;
    }

    // Operadores aritmeticos
    MiniParAny operator+(const MiniParAny& o) const {
        if (kind == Kind::STR || o.kind == Kind::STR) return MiniParAny(std::string(*this) + std::string(o));
        return MiniParAny(num_val + o.num_val);
    }
    MiniParAny operator-(const MiniParAny& o) const { return MiniParAny(num_val - o.num_val); }
    MiniParAny operator*(const MiniParAny& o) const { return MiniParAny(num_val * o.num_val); }
    MiniParAny operator/(const MiniParAny& o) const { return o.num_val != 0.0 ? MiniParAny(num_val / o.num_val) : MiniParAny(0.0); }
    MiniParAny operator%(const MiniParAny& o) const { return MiniParAny(fmod(num_val, o.num_val)); }
    MiniParAny operator-() const { return MiniParAny(-num_val); }
    MiniParAny operator!() const { return MiniParAny(num_val == 0.0 ? 1.0 : 0.0); }

    // Operadores de comparacao
    bool operator==(const MiniParAny& o) const {
        if (kind == Kind::STR && o.kind == Kind::STR) return str_val == o.str_val;
        return num_val == o.num_val;
    }
    bool operator!=(const MiniParAny& o) const { return !(*this == o); }
    bool operator<(const MiniParAny& o) const { return num_val < o.num_val; }
    bool operator<=(const MiniParAny& o) const { return num_val <= o.num_val; }
    bool operator>(const MiniParAny& o) const { return num_val > o.num_val; }
    bool operator>=(const MiniParAny& o) const { return num_val >= o.num_val; }
    bool operator&&(const MiniParAny& o) const { return (bool)*this && (bool)o; }
    bool operator||(const MiniParAny& o) const { return (bool)*this || (bool)o; }
};

// Impressao de MiniParAny no cout
inline std::ostream& operator<<(std::ostream& os, const MiniParAny& v) {
    if (v.kind == MiniParAny::Kind::STR) { os << v.str_val; return os; }
    if (v.kind == MiniParAny::Kind::VEC) {
        os << "[";
        for (std::size_t i = 0; i < v.vec_val.size(); ++i) {
            os << v.vec_val[i];
            if (i != v.vec_val.size() - 1) os << ", ";
        }
        os << "]";
        return os;
    }
    if (v.kind == MiniParAny::Kind::MAT) {
        os << "[";
        for (std::size_t i = 0; i < v.mat_val.size(); ++i) {
            os << "[";
            for (std::size_t j = 0; j < v.mat_val[i].size(); ++j) {
                os << v.mat_val[i][j];
                if (j != v.mat_val[i].size() - 1) os << ", ";
            }
            os << "]";
            if (i != v.mat_val.size() - 1) os << ", ";
        }
        os << "]";
        return os;
    }
    // NUM ou BOOL
    double val = v.num_val;
    if (val == (long long)val) os << (long long)val;
    else os << val;
    return os;
}

// Impressao de vector<MiniParAny> linha de matriz
inline std::ostream& operator<<(std::ostream& os, const MiniParVec& row) {
    os << "[";
    for (std::size_t i = 0; i < row.size(); ++i) {
        os << row[i];
        if (i != row.size() - 1) os << ", ";
    }
    os << "]";
    return os;
}

// =====================================================================
// Helpers globais
// =====================================================================

// Random
double random_val() { return (double)rand() / RAND_MAX; }

// Input do teclado
std::string input() {
    std::string s;
    std::getline(std::cin, s);
    return s;
}
std::string input(const std::string& prompt) {
    std::cout << prompt;
    return input();
}
MiniParAny input(const MiniParAny& prompt) {
    std::cout << prompt;
    std::string s;
    std::getline(std::cin, s);
    return MiniParAny(s);
}

// Range
MiniParAny __minipar_range(double end_val) {
    MiniParVec values;
    for (int i = 0; i < (int)end_val; ++i) values.push_back(MiniParAny((double)i));
    return MiniParAny(values);
}
MiniParAny __minipar_range(double start_val, double end_val) {
    MiniParVec values;
    for (int i = (int)start_val; i < (int)end_val; ++i) values.push_back(MiniParAny((double)i));
    return MiniParAny(values);
}

// Pop de array
MiniParAny __array_pop(MiniParAny& v) {
    if (v.kind == MiniParAny::Kind::VEC && !v.vec_val.empty()) {
        auto val = v.vec_val.back();
        v.vec_val.pop_back();
        return val;
    }
    return MiniParAny(0.0);
}

// Criacao de matriz com valor inicial
MiniParAny __make_matrix(double rows, double cols, const MiniParAny& init_val) {
    MiniParMat m((int)rows, std::vector<MiniParAny>((int)cols, init_val));
    return MiniParAny(m);
}

// Acesso a elemento de matriz (obj[i][j])
// Com MiniParAny, obj[i] retorna a linha (MiniParVec), e [j] acessa o elemento
// Para IndexExpr aninhado: obj[i][j] -> mat_val[i][j]
// O codegen gera: obj[i][j] como obj.mat_val[i][j] via operator[] encadeado
// Mas como operator[] retorna MiniParAny& apenas para VEC,
// precisamos de um helper para acesso a matriz:
inline MiniParAny& __mat_at(MiniParAny& m, int i, int j) {
    return m.mat_val[i][j];
}
inline const MiniParAny& __mat_at(const MiniParAny& m, int i, int j) {
    return m.mat_val[i][j];
}

// exp() para MiniParAny
inline MiniParAny std_exp(const MiniParAny& v) {
    return MiniParAny(std::exp(v.num_val));
}

// to_string para envio por socket
template<typename T>
std::string __to_string(const T& val) {
    if constexpr (std::is_constructible_v<std::string, T>) {
        return std::string(val);
    } else {
        return std::to_string(val);
    }
}
inline std::string __to_string(const MiniParAny& val) {
    if (val.kind == MiniParAny::Kind::STR) return val.str_val;
    return std::to_string(val.num_val);
}

// =====================================================================
// Canal de Comunicacao MiniPar (TCP Sockets)
// =====================================================================
class MiniParChannel {
public:
    std::string ip;
    int port;

    MiniParChannel(std::string ip, int port) : ip(ip), port(port) {}
    MiniParChannel(const MiniParAny& ip_any, const MiniParAny& port_any)
        : ip(ip_any.str_val), port((int)port_any.num_val) {}

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

class Neuronio {
public:
    decltype(1) input_val = 1;
    decltype(0) output_desejado = 0;
    decltype(0.5) peso = 0.5;
    decltype(1) bias = 1;
    decltype(0.5) peso_bias = 0.5;
    decltype(0.01) taxa_aprendizado = 0.01;
    decltype(999) erro = 999;
    decltype(0) iteracao = 0;
    MiniParAny ativacao(MiniParAny soma) {
        if ((soma >= 0))
        {
            return 1;
        }
        return 0;
    }
    void treinar() {
        std::cout << "Entrada:" << " " << this->input_val << " " << "| Saida desejada:" << " " << this->output_desejado << std::endl;
        while ((this->erro != 0))
        {
            this->iteracao = (this->iteracao + 1);
            auto soma = ((this->input_val * this->peso) + (this->bias * this->peso_bias));
            auto saida = this->ativacao(soma);
            this->erro = (this->output_desejado - saida);
            std::cout << "#### Iteracao:" << " " << this->iteracao << std::endl;
            std::cout << "Peso:" << " " << this->peso << std::endl;
            std::cout << "Saida:" << " " << saida << std::endl;
            std::cout << "Erro:" << " " << this->erro << std::endl;
            if ((this->erro != 0))
            {
                this->peso = (this->peso + ((this->taxa_aprendizado * this->input_val) * this->erro));
                this->peso_bias = (this->peso_bias + ((this->taxa_aprendizado * this->bias) * this->erro));
                std::cout << "Peso do bias:" << " " << this->peso_bias << std::endl;
            }
        }
        std::cout << "Parabens! O neuronio aprendeu." << std::endl;
        std::cout << "Valor desejado:" << " " << this->output_desejado << std::endl;
    }
};

int main() {
    #ifdef _WIN32
        WSADATA wsa;
        WSAStartup(MAKEWORD(2,2), &wsa);
    #endif

    auto neuronio = std::make_shared<Neuronio>();
    neuronio->treinar();

    return 0;
}
