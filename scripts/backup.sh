#!/usr/bin/env bash
# MAX Meeting 백업 스크립트
# pg_dump + rsync + GPG 암호화

set -euo pipefail

# 설정
BACKUP_DIR="/home/et/max-ops/max-meeting/backups"
DB_NAME="maxmeeting"
DB_USER="maxmeeting"
DATA_DIR="/home/et/max-ops/max-meeting/data"
RETENTION_DAYS=30

# 타임스탬프
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_SUBDIR="${BACKUP_DIR}/${TIMESTAMP}"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 백업 디렉토리 생성
mkdir -p "${BACKUP_SUBDIR}"

# 1. PostgreSQL 백업
log_info "PostgreSQL 백업 시작..."
if docker exec maxmeeting-db pg_dump -U "${DB_USER}" "${DB_NAME}" > "${BACKUP_SUBDIR}/db_${TIMESTAMP}.sql"; then
    log_info "DB 백업 완료: ${BACKUP_SUBDIR}/db_${TIMESTAMP}.sql"
    # 압축
    gzip "${BACKUP_SUBDIR}/db_${TIMESTAMP}.sql"
    log_info "DB 백업 압축 완료"
else
    log_error "DB 백업 실패"
    exit 1
fi

# 2. 녹음 파일 백업 (rsync - 증분 백업)
log_info "녹음 파일 백업 시작..."
RECORDINGS_BACKUP="${BACKUP_SUBDIR}/recordings"
mkdir -p "${RECORDINGS_BACKUP}"

if [ -d "${DATA_DIR}/recordings" ]; then
    rsync -av --progress "${DATA_DIR}/recordings/" "${RECORDINGS_BACKUP}/"
    log_info "녹음 파일 백업 완료"
else
    log_warn "녹음 디렉토리가 없습니다: ${DATA_DIR}/recordings"
fi

# 3. 필기 데이터 백업
log_info "필기 데이터 백업 시작..."
SKETCHES_BACKUP="${BACKUP_SUBDIR}/sketches"
mkdir -p "${SKETCHES_BACKUP}"

if [ -d "${DATA_DIR}/sketches" ]; then
    rsync -av --progress "${DATA_DIR}/sketches/" "${SKETCHES_BACKUP}/"
    log_info "필기 데이터 백업 완료"
else
    log_warn "필기 디렉토리가 없습니다: ${DATA_DIR}/sketches"
fi

# 4. 백업 압축 (전체)
log_info "전체 백업 압축 중..."
cd "${BACKUP_DIR}"
tar -czf "${TIMESTAMP}.tar.gz" "${TIMESTAMP}"
rm -rf "${TIMESTAMP}"
log_info "백업 압축 완료: ${BACKUP_DIR}/${TIMESTAMP}.tar.gz"

# 5. GPG 암호화 (선택적)
if command -v gpg &> /dev/null && [ -n "${GPG_RECIPIENT:-}" ]; then
    log_info "GPG 암호화 중..."
    gpg --encrypt --recipient "${GPG_RECIPIENT}" "${BACKUP_DIR}/${TIMESTAMP}.tar.gz"
    rm "${BACKUP_DIR}/${TIMESTAMP}.tar.gz"
    log_info "암호화 완료: ${BACKUP_DIR}/${TIMESTAMP}.tar.gz.gpg"
fi

# 6. 오래된 백업 삭제
log_info "오래된 백업 정리 (${RETENTION_DAYS}일 이전)..."
find "${BACKUP_DIR}" -name "*.tar.gz*" -type f -mtime +${RETENTION_DAYS} -delete
log_info "정리 완료"

# 7. 백업 통계
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/${TIMESTAMP}"* 2>/dev/null | cut -f1 || echo "N/A")
log_info "===== 백업 완료 ====="
log_info "타임스탬프: ${TIMESTAMP}"
log_info "백업 크기: ${BACKUP_SIZE}"
log_info "위치: ${BACKUP_DIR}"

exit 0
