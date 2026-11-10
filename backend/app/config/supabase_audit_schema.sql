-- ESPOCH – DI – 060: Sistema de Indicadores Financieros SFPS
-- Esquema de Auditoría, RBAC y Descarga de Microdatos (Supabase / PostgreSQL)

-- 1. Tabla de Logs de Auditoría y Trazabilidad de Cumplimiento
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    user_sub VARCHAR(120) NOT NULL,
    user_role VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Índices para búsqueda rápida de trazabilidad
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_sub ON public.audit_logs (user_sub);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs (timestamp DESC);

-- 2. Políticas de Seguridad RLS (Row Level Security)
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Solo administradores y auditores pueden consultar el registro histórico de auditoría
CREATE POLICY "Auditores y Administradores pueden leer audit_logs"
    ON public.audit_logs
    FOR SELECT
    USING (
        auth.jwt() ->> 'role' IN ('auditor', 'administrador', 'admin')
    );

-- El servicio backend (service_role) tiene inserción y lectura irrestricta
CREATE POLICY "Service Role puede insertar eventos de auditoría"
    ON public.audit_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
