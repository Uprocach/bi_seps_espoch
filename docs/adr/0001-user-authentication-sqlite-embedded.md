# 0001. Autenticación de Usuarios con SQLite Embebido y Contraseñas Temporales

- **Fecha:** 2026-11-10
- **Estado:** Aceptado
- **Decisores:** Investigador Principal / Arquitectura de Software

## Contexto

El sistema de indicadores financieros requería escalar de 3 credenciales fijas de prueba a un padrón de aproximadamente 100 usuarios acreditados (investigadores, auditores de cooperativas y administradores).
El entorno de despliegue objetivo es un servidor propio administrado mediante Portainer con Nginx externo como proxy inverso, sin servidor de correo SMTP configurado para el envío masivo de correos de activación.

## Decisión

1. **Persistencia Autónoma en SQLite:** Implementar una base de datos local SQLite (`data/users.db`) montada como volumen persistente en `docker-compose.yml`, evitando la sobrecarga de dependencias de servicios externos de bases de datos relacionales para autenticación.
2. **Criptografía PBKDF2-SHA256:** Cifrar las contraseñas con el estándar `hashlib.pbkdf2_hmac` de 100,000 iteraciones y salt aleatorio de 16 bytes.
3. **Contraseñas Temporales por Convención:** La contraseña inicial por defecto de los usuarios institucionales coincide con su identificador de correo (ej. `nombre.apellido` para `nombre.apellido@espoch.edu.ec`).
4. **Bandera de Cambio Obligatorio:** Todo usuario creado o importado inicia con `must_change_password = 1`. Al ingresar, un modal interceptor le exige establecer su clave definitiva antes de navegar.
5. **Panel Administrativo:** Dotar a los administradores de endpoints y una interfaz visual en React para altas individuales, importación masiva por CSV y restablecimiento de claves.

## Consecuencias

### Positivas
- 100% autónomo y desacoplado de la nube externa.
- No requiere configuración de servidores SMTP para invitar usuarios.
- Tiempos de validación criptográfica sub-milisegundo.
- Persistencia garantizada ante reinicios o actualizaciones de la imagen Docker en Portainer.

### Negativas / Mitigaciones
- Si un usuario olvida su contraseña, debe solicitar el restablecimiento manual al administrador (mitigado mediante el botón de 1 clic en la pantalla de administración).
