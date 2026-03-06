import Foundation

// MARK: - Health

public struct HealthResponse: Codable {
    public let status: String
    public let machine: String?
    public let project: String?

    public init(status: String, machine: String?, project: String?) {
        self.status = status
        self.machine = machine
        self.project = project
    }
}

// MARK: - NFA Consult

public struct NFAConsultRequest: Encodable {
    public let data_inicial: String
    public let data_final: String
    public let matricula: String?
    public let username: String?
    public let password: String?

    public init(data_inicial: String, data_final: String, matricula: String?, username: String?, password: String?) {
        self.data_inicial = data_inicial
        self.data_final = data_final
        self.matricula = matricula
        self.username = username
        self.password = password
    }
}

public struct NFAConsultResponse: Codable {
    public let job_id: String
    public let status: String

    public init(job_id: String, status: String) {
        self.job_id = job_id
        self.status = status
    }
}

public struct NFAJobStatusResponse: Codable {
    public let job_id: String
    public let job_type: String
    public let status: String
    public let created_at: String
    public let started_at: String?
    public let completed_at: String?
    public let nfa_numero: String?
    public let danfe_path: String?
    public let dar_path: String?
    public let result: [String: String]?
    public let error: String?
}

// MARK: - REDESIM Consulta

public struct CadRedesimConsultaRequest: Encodable {
    public let data_criacao_inicio: String?
    public let data_criacao_fim: String?
    public let wait_user_dates: Bool?
    public let username: String?
    public let password: String?

    public init(data_criacao_inicio: String?, data_criacao_fim: String?, wait_user_dates: Bool?, username: String?, password: String?) {
        self.data_criacao_inicio = data_criacao_inicio
        self.data_criacao_fim = data_criacao_fim
        self.wait_user_dates = wait_user_dates
        self.username = username
        self.password = password
    }
}

public struct CadRedesimConsultaResponse: Codable {
    public let job_id: String
    public let status: String
    public let execution_id: String?

    public init(job_id: String, status: String, execution_id: String?) {
        self.job_id = job_id
        self.status = status
        self.execution_id = execution_id
    }
}

public struct CadRedesimJobStatusResponse: Codable {
    public let job_id: String
    public let status: String
    public let result: [String: String]?
    public let error: String?
}

// MARK: - FAC

public struct FACItem: Codable {
    public let processo: String
    public let fac: String?
    public let interessado: String?
}

public struct FACBatchRequest: Codable {
    public let facs: [FACItem]
    public let credentials: [String: String]?
    public let options: [String: Bool]?
}

public struct FACBatchResponse: Codable {
    public let success: Bool
    public let job_id: String
    public let total: Int
    public let processed: Int
    public let results: [[String: String]]?
    public let errors: [String]?
}

// MARK: - CEP

public struct CEPValidationRequest: Encodable {
    public let cep: String
    public let enrich: Bool?

    public init(cep: String, enrich: Bool?) {
        self.cep = cep
        self.enrich = enrich
    }
}

public struct CEPValidationResponse: Codable {
    public let success: Bool
    public let data: CEPData?
    public let errors: [String]
}

public struct CEPData: Codable {
    public let cep: String?
    public let valid: Bool?
    public let logradouro: String?
    public let bairro: String?
    public let cidade: String?
    public let uf: String?
    public let ibge: String?
    public let source: String?
}

// MARK: - Executor

public struct ScriptExecutionRequest: Encodable {
    public let script_content: String
    public let timeout: Int

    public init(script_content: String, timeout: Int) {
        self.script_content = script_content
        self.timeout = timeout
    }
}

public struct ScriptExecutionResponse: Codable {
    public let success: Bool
    public let exit_code: Int
    public let stdout: String
    public let stderr: String
    public let duration_ms: Int
}
