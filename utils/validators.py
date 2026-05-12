from utils.logger import logger


def _get_primeiro(dados: dict, chaves: list[str]):
    for chave in chaves:
        if chave in dados:
            return dados.get(chave)
    return None


def normalizar_chave_acesso(chave: object) -> str:
    """Normaliza a chave da NF-e para apenas 44 digitos."""
    if chave is None:
        return ""
    digits = "".join(char for char in str(chave).strip() if char.isdigit())
    return digits if len(digits) == 44 else ""


def validar_chave_acesso(chave: object) -> bool:
    """
    Valida se a chave de acesso tem o formato correto (44 dígitos).
    """
    return bool(normalizar_chave_acesso(chave))


def validar_placa(placa: str) -> bool:
    """
    Valida se a placa não está vazia.
    """
    return bool(placa and str(placa).strip())


def validar_rota(rota: str) -> bool:
    """
    Valida se a rota não está vazia.
    """
    return bool(rota and str(rota).strip())


def validar_linha_planilha(dados: dict, tipo_separacao: str) -> bool:
    """
    Valida se uma linha da planilha tem os dados necessários.
    
    Args:
        dados: Dicionário com dados da linha
        tipo_separacao: 'placa' ou 'rota'
    
    Returns:
        True se válido, False caso contrário
    """
    # Chave é obrigatória (aceita chaves do Excel e do modelo)
    chave = _get_primeiro(dados, ["CHAVE", "Chave de acesso", "chave"])
    if not validar_chave_acesso(chave):
        logger.warning(f"Chave inválida: {chave}")
        return False
    
    # Validar conforme tipo de separação
    if tipo_separacao == "placa":
        placa = _get_primeiro(dados, ["Placa", "placa"])
        if not validar_placa(placa):
            logger.warning(f"Placa inválida: {placa}")
            return False
    elif tipo_separacao == "rota":
        rota = _get_primeiro(dados, ["Identificador da rota", "Identificador", "rota"])
        if not validar_rota(rota):
            logger.warning(f"Rota inválida: {rota}")
            return False
    
    return True
