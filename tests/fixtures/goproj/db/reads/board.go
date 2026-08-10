package reads

// 조회 전용 레이어인데 삭제 SQL 이 있다.
func PurgeCache(conn *DB) {
	conn.Exec("DELETE FROM board_cache")
}
