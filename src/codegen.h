#pragma once
#include "ast.h"
#include <string>
#include <memory>

class CppCodeGenerator {
private:
    std::string translateNode(std::shared_ptr<ASTNode> node);
    std::string translateStatement(std::shared_ptr<ASTNode> node, const std::string& indent);
    std::string translateExpression(std::shared_ptr<ASTNode> node);
    std::string escapeString(const std::string& value);

public:
    void generate(std::shared_ptr<Program> program, const std::string& outputName);
};
