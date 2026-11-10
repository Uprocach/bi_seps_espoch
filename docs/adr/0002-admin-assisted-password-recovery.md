# 0002. Política de Recuperación de Contraseñas Asistida (Sin SMTP)

- **Fecha:** 2026-11-10
- **Estado:** Aceptado
- **Decisores:** Investigador Principal / Arquitectura de Software

## Contexto

Se analizó la necesidad de un flujo de recuperación de contraseñas para los ~100 usuarios acreditados de la plataforma ante posibles olvidos de credenciales personales. Se evaluaron dos alternativas:
1. Implementar autoservicio mediante correo electrónico transaccional (SMTP).
2. Mantener un modelo asistido por el Administrador mediante el panel institucional.

## Decisión

Se decide **rechazar la implementación de servidores de correo SMTP** y formalizar el **Restablecimiento Asistido por el Administrador**:
1. El sistema es analítico, cerrado y con un padrón de usuarios relativamente estático institucionalmente delimitado (ESPOCH y cooperativas supervisadas).
2. Integrar SMTP añadiría sobrecarga operativa innecesaria (mantenimiento de credenciales de correo, riesgo de bloqueo por spam y dependencias de red externas).
3. El Administrador cuenta con la facultad operativa de restablecer en un clic la clave de cualquier usuario a su convención institucional (`nombre.apellido`), reactivando de inmediato la bandera `must_change_password = true`.
4. La interfaz de autenticación pública (`LoginModal`) incluye un canal visible de asistencia y soporte institucional.

## Consecuencias

- **Autonomía total:** Cero dependencias de proveedores de email transaccional (SendGrid, Mailgun o SMTP).
- **Trazabilidad:** Cada restablecimiento queda registrado en la bitácora de auditoría inmutable (`audit_logs`) con el usuario administrador responsable y la fecha exacta.
