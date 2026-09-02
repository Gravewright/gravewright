# Security policy / Política de segurança

## English

### Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories for the Gravewright repository. Do not open a public issue before a fix is available. Include the affected version, impact, reproduction, and suggested mitigation when possible. Never attach real credentials, private module archives, or personal data.

The latest commit on `main` is the currently supported pre-1.0 line. The team will acknowledge, assess, coordinate a fix, and publish disclosure information when appropriate; response or remediation deadlines are not guaranteed.

### Security model

Modules execute with the permissions of the host Node.js process. Manifest validation, explicit exports, dependency checks, hashes, and package policies reduce particular risks; they do **not** sandbox module code or establish its trustworthiness. Review module source and provenance, pin trusted versions, verify release hashes, limit host permissions, and keep secrets outside source control.

Security fixes may tighten validation of manifests, archives, URLs, lockfiles, network targets, or npm configuration even when unsafe input previously appeared to work. Insecure behavior is not a supported contract.

## Português

### Como reportar uma vulnerabilidade

Reporte suspeitas em privado pelos GitHub Security Advisories do repositório Gravewright. Não abra issue pública antes da correção. Quando possível, informe versão afetada, impacto, reprodução e mitigação sugerida. Nunca anexe credenciais reais, arquivos privados de módulos ou dados pessoais.

O commit mais recente de `main` é a linha pré-1.0 atualmente suportada. A equipe fará a triagem e coordenará a correção e a divulgação quando apropriado, sem garantia de prazo de resposta ou remediação.

### Modelo de segurança

Módulos executam com as permissões do processo Node.js hospedeiro. Validação de manifest, exports explícitos, verificação de dependências, hashes e políticas de pacotes reduzem riscos específicos; não isolam o código nem comprovam sua confiabilidade. Revise a origem e o código, fixe versões confiáveis, confira hashes, restrinja permissões e mantenha segredos fora do controle de versão.

Correções podem tornar mais estrita a validação de manifests, arquivos, URLs, lockfiles, destinos de rede ou npm. Comportamento inseguro não é um contrato suportado e pode ser bloqueado mesmo em uma versão de correção.
