# O pacote instalado se chama "webrtcvad-wheels", mas o módulo é "webrtcvad".
# A regra padrão do PyInstaller procura os metadados com o nome errado e quebra a montagem;
# esta substitui aquela. O módulo é um único arquivo binário, coletado automaticamente.
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("webrtcvad-wheels")
