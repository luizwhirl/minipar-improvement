#pragma once
#include "ast.h"
#include <string>
#include <memory>

class CppCodeGenerator {
private:
    std::string translateNode(std::shared_ptr<ASTNode> node);

public:
    void generate(std::shared_ptr<Program> program, const std::string& outputName);
};