"""Writes what the pipeline does into etl.run_log and etl.step_log (the ETL metadata).

These functions use their own connection in autocommit mode, so a log line is saved at once and
stays saved even when the step it describes fails and is rolled back.
"""


def start_run(log, fresh=False):
    """Return (run_id, steps_already_done).

    If the last run failed (or was interrupted), continue that run: same run_id, and the steps that
    already succeeded are skipped. With fresh=True the failed run is given up ('abandoned') and a new
    run starts from step 1, so everything is read and built again. Otherwise start a new run.
    """
    last = log.execute("SELECT run_id, status FROM etl.run_log ORDER BY run_id DESC LIMIT 1").fetchone()
    if last and last[1] in ("failed", "running"):
        if fresh:
            log.execute("UPDATE etl.run_log SET status = 'abandoned' WHERE run_id = %s", [last[0]])
        else:
            run_id = last[0]
            log.execute("UPDATE etl.run_log SET status = 'running', finished_at = NULL WHERE run_id = %s", [run_id])
            done = log.execute(
                "SELECT step_name FROM etl.step_log WHERE run_id = %s AND status = 'success'", [run_id]
            ).fetchall()
            return run_id, {row[0] for row in done}

    run_id = log.execute("INSERT INTO etl.run_log (status) VALUES ('running') RETURNING run_id").fetchone()[0]
    return run_id, set()


def start_step(log, run_id, step_name):
    """Record that a step started. Returns the id of the new log row."""
    return log.execute(
        "INSERT INTO etl.step_log (run_id, step_name, status) VALUES (%s, %s, 'running') RETURNING step_log_id",
        [run_id, step_name],
    ).fetchone()[0]


def end_step(log, step_log_id, status, row_count=None, error_message=None):
    """Record how a step ended: 'success' or 'failed'."""
    log.execute(
        "UPDATE etl.step_log SET status = %s, finished_at = now(), row_count = %s, error_message = %s"
        " WHERE step_log_id = %s",
        [status, row_count, error_message, step_log_id],
    )


def end_run(log, run_id, status):
    """Record how the whole run ended: 'success' or 'failed'."""
    log.execute("UPDATE etl.run_log SET status = %s, finished_at = now() WHERE run_id = %s", [status, run_id])
