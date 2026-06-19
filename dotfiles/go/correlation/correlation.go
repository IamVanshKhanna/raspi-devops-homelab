# Correlation ID Middleware for Go Services
# Usage: Import this package and wrap your HTTP handlers

package correlation

import (
	"context"
	"net/http"
	"strings"

	"github.com/google/uuid"
)

const (
	CorrelationIDHeader = "X-Correlation-ID"
	CorrelationIDContextKey = "correlation_id"
)

func Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		correlationID := r.Header.Get(CorrelationIDHeader)
		if correlationID == "" {
			correlationID = uuid.New().String()
		}

		w.Header().Set(CorrelationIDHeader, correlationID)

		ctx := context.WithValue(r.Context(), CorrelationIDContextKey, correlationID)
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

func GetCorrelationID(ctx context.Context) string {
	if id, ok := ctx.Value(CorrelationIDContextKey).(string); ok {
		return id
	}
	return ""
}

func SetCorrelationIDHeader(w http.ResponseWriter, correlationID string) {
	w.Header().Set(CorrelationIDHeader, correlationID)
}

func PropagateCorrelationID(r *http.Request) *http.Request {
	correlationID := GetCorrelationID(r.Context())
	if correlationID != "" {
		r.Header.Set(CorrelationIDHeader, r.Header.Get("X-Correlation-ID"))
	}
	return r
}