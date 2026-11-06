import pytest

from coleta.publicador import Publicador


def test_publicar_sem_broker_nao_levanta():
    publicador = Publicador("127.0.0.1", 1, "placa01")
    publicador.conectar()
    assert publicador.publicar("leituras", {"x": 1}) is False
    assert publicador.conectado is False
    publicador.encerrar()


def test_tipo_invalido_levanta():
    with pytest.raises(ValueError):
        Publicador("127.0.0.1", 1, "placa01").publicar("outro", {})
