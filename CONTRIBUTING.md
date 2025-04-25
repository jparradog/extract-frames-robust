# Contribuir

¡Gracias por tu interés en contribuir a Extract Frames Robust! Sigue estos pasos:

## Reportar errores
- Abre un _issue_ usando la plantilla de bug report.
- Proporciona descripción clara, pasos para reproducir y contexto.

## Proponer mejoras
- Abre un _issue_ de feature request describiendo la necesidad y el caso de uso.

## Pull Requests
1. Haz un fork del repositorio.
2. Crea una rama con nombre descriptivo (`feature/nombre`, `fix/descripcion`).
3. Escribe código limpio y comentado.
4. Asegúrate de que **todas** las pruebas pasen:

   ```bash
   poetry run pytest
   ```

5. Abre el PR apuntando a `main`, siguiendo la plantilla de Pull Request.
6. Responde a feedback y haz squash de commits si es necesario.

## Estilo de código
- Sigue las reglas de [flake8](.flake8) y [black](https://black.readthedocs.io/).
- Escribe tests para nuevas funcionalidades.
