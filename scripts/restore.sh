#!/usr/bin/env bash
# MAX Meeting 복원 스크립트
# 백업 파일에서 데이터 복원

set -euo pipefail

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 사용법
usage() {
    cat << EOF
Usage: $0 <backup_file> [options]

Arguments:
  backup_file       백업 파일 경로 (.tar.gz or .tar.gz.gpg)

Options:
  --db-only         데이터베이스만 복원
  --files-only      파일(녹음/필기)만 복원
  --no-confirm      확인 없이 복원 (주의!)
  -h, --help        도움말 표시

Examples:
  $0 backups/20240128_120000.tar.gz
  $0 backups/20240128_120000.tar.gz.gpg --db-only
  $0 backups/20240128_120000.tar.gz --files-only

EOF
    exit 1
}

# 인자 검사
if [ $# -lt 1 ]; then
    log_error "백업 파일 경로가 필요합니다"
    usage
fi

BACKUP_FILE="$1"
shift

# 옵션 파싱
DB_ONLY=false
FILES_ONLY=false
NO_CONFIRM=false

while [ $# -gt 0 ]; do
    case "$1" in
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --files-only)
            FILES_ONLY=true
            shift
            ;;
        --no-confirm)
            NO_CONFIRM=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            usage
            ;;
    esac
done

# 백업 파일 존재 확인
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "백업 파일이 없습니다: ${BACKUP_FILE}"
    exit 1
fi

# 설정
RESTORE_DIR="/tmp/maxmeeting_restore_$$"
DB_NAME="maxmeeting"
DB_USER="maxmeeting"
DATA_DIR="/home/et/max-ops/max-meeting/data"

# 경고
if [ "${NO_CONFIRM}" = false ]; then
    log_warn "===== 경고 ====="
    log_warn "이 작업은 기존 데이터를 덮어씁니다!"
    log_warn "백업 파일: ${BACKUP_FILE}"
    [ "${DB_ONLY}" = true ] && log_warn "복원 범위: 데이터베이스만"
    [ "${FILES_ONLY}" = true ] && log_warn "복원 범위: 파일만"
    [ "${DB_ONLY}" = false ] && [ "${FILES_ONLY}" = false ] && log_warn "복원 범위: 전체"
    echo ""
    read -p "계속하시겠습니까? (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        log_info "복원 취소됨"
        exit 0
    fi
fi

# 임시 디렉토리 생성
mkdir -p "${RESTORE_DIR}"
trap "rm -rf ${RESTORE_DIR}" EXIT

# 1. GPG 복호화 (필요시)
EXTRACT_FILE="${BACKUP_FILE}"
if [[ "${BACKUP_FILE}" == *.gpg ]]; then
    log_info "GPG 복호화 중..."
    DECRYPTED_FILE="${RESTORE_DIR}/decrypted.tar.gz"
    if gpg --decrypt --output "${DECRYPTED_FILE}" "${BACKUP_FILE}"; then
        log_info "복호화 완료"
        EXTRACT_FILE="${DECRYPTED_FILE}"
    else
        log_error "복호화 실패"
        exit 1
    fi
fi

# 2. 압축 해제
log_info "백업 파일 압축 해제 중..."
if tar -xzf "${EXTRACT_FILE}" -C "${RESTORE_DIR}"; then
    log_info "압축 해제 완료"
else
    log_error "압축 해제 실패"
    exit 1
fi

# 백업 디렉토리 찾기
BACKUP_SUBDIR=$(find "${RESTORE_DIR}" -maxdepth 1 -type d ! -path "${RESTORE_DIR}" | head -n 1)
if [ -z "${BACKUP_SUBDIR}" ]; then
    log_error "백업 데이터를 찾을 수 없습니다"
    exit 1
fi

# 3. 데이터베이스 복원
if [ "${FILES_ONLY}" = false ]; then
    log_info "데이터베이스 복원 시작..."

    DB_DUMP=$(find "${BACKUP_SUBDIR}" -name "db_*.sql.gz" | head -n 1)
    if [ -z "${DB_DUMP}" ]; then
        log_error "DB 백업 파일을 찾을 수 없습니다"
        exit 1
    fi

    # 압축 해제
    gunzip -c "${DB_DUMP}" > "${RESTORE_DIR}/restore.sql"

    # 기존 DB 드롭 및 재생성
    log_warn "기존 데이터베이스 삭제 및 재생성..."
    docker exec maxmeeting-db psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" || true
    docker exec maxmeeting-db psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

    # 복원
    if docker exec -i maxmeeting-db psql -U "${DB_USER}" -d "${DB_NAME}" < "${RESTORE_DIR}/restore.sql"; then
        log_info "데이터베이스 복원 완료"
    else
        log_error "데이터베이스 복원 실패"
        exit 1
    fi
fi

# 4. 파일 복원
if [ "${DB_ONLY}" = false ]; then
    # 녹음 파일 복원
    if [ -d "${BACKUP_SUBDIR}/recordings" ]; then
        log_info "녹음 파일 복원 시작..."
        mkdir -p "${DATA_DIR}/recordings"
        rsync -av --progress "${BACKUP_SUBDIR}/recordings/" "${DATA_DIR}/recordings/"
        log_info "녹음 파일 복원 완료"
    else
        log_warn "녹음 파일 백업이 없습니다"
    fi

    # 필기 데이터 복원
    if [ -d "${BACKUP_SUBDIR}/sketches" ]; then
        log_info "필기 데이터 복원 시작..."
        mkdir -p "${DATA_DIR}/sketches"
        rsync -av --progress "${BACKUP_SUBDIR}/sketches/" "${DATA_DIR}/sketches/"
        log_info "필기 데이터 복원 완료"
    else
        log_warn "필기 데이터 백업이 없습니다"
    fi
fi

log_info "===== 복원 완료 ====="
log_info "백업 소스: ${BACKUP_FILE}"

# 권한 수정 (필요시)
if [ -d "${DATA_DIR}" ]; then
    log_info "파일 권한 재설정 중..."
    chown -R et:et "${DATA_DIR}" 2>/dev/null || true
fi

exit 0
