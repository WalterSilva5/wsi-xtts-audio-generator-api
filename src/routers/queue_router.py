"""Queue management endpoints."""
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.queue import (
    FileQueue, QueueTask, TaskStatus, TaskType,
    TaskResponse, QueueStats, get_consumer
)
from src.audio.converter import estimate_duration_seconds


router = APIRouter(
    prefix="/queue",
    tags=["queue"]
)


class EnqueueSynthesisRequest(BaseModel):
    """Request to enqueue a synthesis task."""
    text: str
    voice: str = "voice"
    lang_code: str = "en"
    output_format: str = "wav"
    temperature: float = Field(default=0.65, ge=0.0, le=1.0)
    length_penalty: float = Field(default=1.0, ge=0.5, le=2.0)
    repetition_penalty: float = Field(default=12.0, ge=1.0, le=20.0)
    top_k: int = Field(default=35, ge=1, le=100)
    top_p: float = Field(default=0.75, ge=0.0, le=1.0)
    speed: float = Field(default=0.95, ge=0.5, le=2.0)
    do_sample: bool = True
    enable_text_splitting: bool = True


class EnqueueBatchRequest(BaseModel):
    """Request to enqueue a batch synthesis task."""
    items: List[dict]
    default_voice: str = "voice"
    default_lang_code: str = "en"
    output_format: str = "wav"


class EnqueueResponse(BaseModel):
    """Response after enqueuing a task."""
    task_id: str
    status: str
    position_in_queue: int
    estimated_wait_seconds: Optional[float] = None
    message: str


queue = FileQueue()


def _get_queue_position(task_id: str) -> int:
    """Get position of task in queue (1-based)."""
    pending = queue.get_all_tasks(TaskStatus.PENDING)
    for i, task in enumerate(pending):
        if task.id == task_id:
            return i + 1
    return 0


def _estimate_wait_time(position: int) -> float:
    """Estimate wait time based on queue position."""
    pending_tasks = queue.get_all_tasks(TaskStatus.PENDING)
    total_duration = 0.0

    for i, task in enumerate(pending_tasks):
        if i >= position:
            break
        if task.task_type == TaskType.SYNTHESIS.value:
            text = task.payload.get('text', '')
            speed = task.payload.get('speed', 1.0)
            total_duration += estimate_duration_seconds(text, speed) * 2
        else:
            items = task.payload.get('items', [])
            for item in items:
                total_duration += estimate_duration_seconds(item.get('text', '')) * 2

    return round(total_duration, 1)


@router.post("/enqueue/synthesis", response_model=EnqueueResponse)
async def enqueue_synthesis(request: EnqueueSynthesisRequest):
    """Add a synthesis task to the queue.

    Returns immediately with task ID. Use /queue/task/{task_id} to check status.
    Use /queue/task/{task_id}/result to download the result when completed.
    """
    task = QueueTask(
        task_type=TaskType.SYNTHESIS,
        payload=request.dict()
    )

    task_id = queue.add_task(task)
    position = _get_queue_position(task_id)
    wait_time = _estimate_wait_time(position)

    consumer = get_consumer()
    if not consumer.is_running:
        consumer.start()

    return EnqueueResponse(
        task_id=task_id,
        status="pending",
        position_in_queue=position,
        estimated_wait_seconds=wait_time,
        message=f"Task enqueued successfully. Position: {position}"
    )


@router.post("/enqueue/batch", response_model=EnqueueResponse)
async def enqueue_batch(request: EnqueueBatchRequest):
    """Add a batch synthesis task to the queue.

    Returns a ZIP file containing all audio files when completed.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Items list cannot be empty")

    task = QueueTask(
        task_type=TaskType.BATCH_SYNTHESIS,
        payload=request.dict()
    )

    task_id = queue.add_task(task)
    position = _get_queue_position(task_id)
    wait_time = _estimate_wait_time(position)

    consumer = get_consumer()
    if not consumer.is_running:
        consumer.start()

    return EnqueueResponse(
        task_id=task_id,
        status="pending",
        position_in_queue=position,
        estimated_wait_seconds=wait_time,
        message=f"Batch task enqueued with {len(request.items)} items. Position: {position}"
    )


@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get the status of a queued task."""
    task = queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    position = 0
    wait_time = None

    if task.status == TaskStatus.PENDING.value:
        position = _get_queue_position(task_id)
        wait_time = _estimate_wait_time(position)

    return TaskResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        result_file=task.result_file,
        error_message=task.error_message,
        created_at=task.created_at.isoformat() if task.created_at else None,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        estimated_wait_seconds=wait_time
    )


@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Download the result of a completed task."""
    task = queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task.status}"
        )

    if not task.result_file or not os.path.exists(task.result_file):
        raise HTTPException(status_code=404, detail="Result file not found")

    filename = os.path.basename(task.result_file)
    media_type = "application/zip" if filename.endswith('.zip') else "audio/wav"

    if filename.endswith('.mp3'):
        media_type = "audio/mpeg"
    elif filename.endswith('.ogg'):
        media_type = "audio/ogg"
    elif filename.endswith('.flac'):
        media_type = "audio/flac"

    return FileResponse(
        task.result_file,
        media_type=media_type,
        filename=filename
    )


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending task."""
    task = queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.status != TaskStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task.status}"
        )

    success = queue.cancel_task(task_id)

    if success:
        return {"success": True, "message": f"Task {task_id} cancelled"}
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List all tasks in the queue, optionally filtered by status."""
    task_status = None
    if status:
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid: pending, processing, completed, failed, cancelled"
            )

    tasks = queue.get_all_tasks(task_status)

    tasks.sort(key=lambda t: t.created_at or "", reverse=True)

    paginated = tasks[offset:offset + limit]

    return [
        TaskResponse(
            id=t.id,
            task_type=t.task_type,
            status=t.status,
            progress=t.progress,
            result_file=t.result_file,
            error_message=t.error_message,
            created_at=t.created_at.isoformat() if t.created_at else None,
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None
        )
        for t in paginated
    ]


@router.get("/stats", response_model=QueueStats)
async def get_queue_stats():
    """Get queue statistics."""
    stats = queue.get_stats()
    consumer = get_consumer()

    return QueueStats(
        total_tasks=stats['total'],
        pending=stats['pending'],
        processing=stats['processing'],
        completed=stats['completed'],
        failed=stats['failed'],
        cancelled=stats['cancelled'],
        consumer_running=consumer.is_running
    )


@router.post("/consumer/start")
async def start_queue_consumer():
    """Start the queue consumer (if not already running)."""
    consumer = get_consumer()

    if consumer.is_running:
        return {"success": False, "message": "Consumer is already running"}

    consumer.start()
    return {"success": True, "message": "Consumer started"}


@router.post("/consumer/stop")
async def stop_queue_consumer():
    """Stop the queue consumer."""
    consumer = get_consumer()

    if not consumer.is_running:
        return {"success": False, "message": "Consumer is not running"}

    consumer.stop()
    return {"success": True, "message": "Consumer stopped"}


@router.post("/cleanup")
async def cleanup_old_tasks(older_than_hours: int = 24):
    """Remove completed/failed/cancelled tasks older than specified hours."""
    removed = queue.clear_completed(older_than_hours)
    return {
        "success": True,
        "removed_count": removed,
        "message": f"Removed {removed} old tasks"
    }
