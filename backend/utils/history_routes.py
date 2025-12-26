# routes/history.py - FASTAPI HISTORY ROUTES
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from models.history import (
    add_history_entry,
    get_user_history,
    get_history_by_type,
    get_history_by_id,
    delete_history_entry,
    clear_user_history,
    get_history_count,
    get_history_stats,
    search_history,
    get_recent_history,
    HistoryModel,
    AddHistoryRequest,
    HistoryStatsModel
)
from models.query import (
    get_queries_by_user,
    get_query_stats,
    get_recent_queries
)
from core.auth import get_current_user
from core.responses import (
    success_response,
    created_response,
    not_found_response,
    no_content_response,
    error_response
)
from config.logging_config import logger


router = APIRouter(prefix="/api/history", tags=["history"])


# ============================================================================
# HISTORY MANAGEMENT
# ============================================================================

@router.post("", status_code=201)
async def add_history(
    data: AddHistoryRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Add a history entry
    
    - **action**: Action type (view/chat/search/process)
    - **resourceType**: Resource type (video/document/chat)
    - **resourceId**: Resource ID
    - **metadata**: Additional metadata
    """
    try:
        history_id = await add_history_entry(
            user_id=user_id,
            action=data.action,
            resource_type=data.resourceType,
            resource_id=data.resourceId,
            metadata=data.metadata or {}
        )
        
        return created_response(
            data={"historyId": history_id},
            message="History entry added",
            resource_id=history_id
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to add history: {e}")
        return error_response(str(e), 500)


@router.get("")
async def get_history(
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter last N days"),
    user_id: str = Depends(get_current_user)
):
    """
    Get user history
    
    - **limit**: Maximum entries to return
    - **skip**: Number to skip (pagination)
    - **action**: Filter by action type
    - **resource_type**: Filter by resource type
    - **days**: Filter last N days
    """
    try:
        # Calculate start date if days specified
        start_date = None
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
        
        history = await get_user_history(
            user_id=user_id,
            limit=limit,
            skip=skip,
            action=action,
            resource_type=resource_type,
            start_date=start_date
        )
        
        total = await get_history_count(user_id)
        
        return success_response(
            data={
                "history": history,
                "total": total,
                "count": len(history)
            },
            message=f"Retrieved {len(history)} history entries"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get history: {e}")
        return error_response(str(e), 500)


@router.get("/recent")
async def get_recent(
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """
    Get recent history entries
    
    - **limit**: Number of entries to return
    """
    try:
        history = await get_recent_history(user_id, limit)
        
        return success_response(
            data={"history": history, "count": len(history)},
            message=f"Retrieved {len(history)} recent entries"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent history: {e}")
        return error_response(str(e), 500)


@router.get("/stats")
async def get_stats(
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user)
):
    """
    Get history statistics
    
    - **days**: Time period in days
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        stats = await get_history_stats(user_id, start_date)
        
        return success_response(
            data=stats,
            message="History statistics retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        return error_response(str(e), 500)


@router.get("/by-type/{resource_type}")
async def get_by_type(
    resource_type: str,
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user)
):
    """
    Get history by resource type
    
    - **resource_type**: Resource type (video/document/chat)
    - **limit**: Maximum entries
    """
    try:
        history = await get_history_by_type(user_id, resource_type, limit)
        
        return success_response(
            data={"history": history, "count": len(history)},
            message=f"Retrieved {len(history)} {resource_type} history entries"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get history by type: {e}")
        return error_response(str(e), 500)


@router.get("/search")
async def search_user_history(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """
    Search history entries
    
    - **q**: Search query
    - **limit**: Maximum results
    """
    try:
        history = await search_history(user_id, q, limit)
        
        return success_response(
            data={"history": history, "count": len(history)},
            message=f"Found {len(history)} matching entries"
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return error_response(str(e), 500)


@router.get("/{history_id}")
async def get_history_entry(
    history_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get specific history entry
    
    - **history_id**: History entry ID
    """
    try:
        entry = await get_history_by_id(user_id, history_id)
        
        if not entry:
            return not_found_response("History entry", history_id)
        
        return success_response(
            data=entry,
            message="History entry retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get history entry: {e}")
        return error_response(str(e), 500)


@router.delete("/{history_id}", status_code=204)
async def delete_history(
    history_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Delete a history entry
    
    - **history_id**: History entry ID
    """
    try:
        deleted = await delete_history_entry(user_id, history_id)
        
        if not deleted:
            return not_found_response("History entry", history_id)
        
        return no_content_response()
        
    except Exception as e:
        logger.error(f"❌ Failed to delete history entry: {e}")
        return error_response(str(e), 500)


@router.delete("")
async def clear_history(
    confirm: bool = Query(..., description="Confirm deletion"),
    older_than_days: Optional[int] = Query(None, ge=1, description="Delete entries older than N days"),
    user_id: str = Depends(get_current_user)
):
    """
    Clear user history
    
    - **confirm**: Must be true to confirm deletion
    - **older_than_days**: Optional - only delete entries older than N days
    """
    try:
        if not confirm:
            return error_response("Confirmation required to clear history", 400)
        
        # Calculate cutoff date if specified
        before_date = None
        if older_than_days:
            before_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        count = await clear_user_history(user_id, before_date)
        
        message = f"Cleared {count} history entries"
        if older_than_days:
            message += f" older than {older_than_days} days"
        
        return success_response(
            data={"deletedCount": count},
            message=message
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to clear history: {e}")
        return error_response(str(e), 500)


# ============================================================================
# ACTIVITY TIMELINE
# ============================================================================

@router.get("/timeline/daily")
async def get_daily_timeline(
    days: int = Query(7, ge=1, le=90),
    user_id: str = Depends(get_current_user)
):
    """
    Get daily activity timeline
    
    - **days**: Number of days to include
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get history with date grouping
        history = await get_user_history(
            user_id=user_id,
            limit=1000,
            start_date=start_date
        )
        
        # Group by date
        timeline = {}
        for entry in history:
            date = entry.get('createdAt', datetime.utcnow()).date().isoformat()
            
            if date not in timeline:
                timeline[date] = {
                    'date': date,
                    'count': 0,
                    'actions': {}
                }
            
            timeline[date]['count'] += 1
            
            action = entry.get('action', 'unknown')
            timeline[date]['actions'][action] = timeline[date]['actions'].get(action, 0) + 1
        
        # Convert to sorted list
        timeline_list = sorted(timeline.values(), key=lambda x: x['date'], reverse=True)
        
        return success_response(
            data={
                "timeline": timeline_list,
                "days": days,
                "totalEntries": len(history)
            },
            message=f"Retrieved {days}-day activity timeline"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get timeline: {e}")
        return error_response(str(e), 500)


@router.get("/timeline/hourly")
async def get_hourly_timeline(
    hours: int = Query(24, ge=1, le=168),
    user_id: str = Depends(get_current_user)
):
    """
    Get hourly activity timeline
    
    - **hours**: Number of hours to include
    """
    try:
        start_date = datetime.utcnow() - timedelta(hours=hours)
        
        history = await get_user_history(
            user_id=user_id,
            limit=1000,
            start_date=start_date
        )
        
        # Group by hour
        timeline = {}
        for entry in history:
            timestamp = entry.get('createdAt', datetime.utcnow())
            hour_key = timestamp.strftime('%Y-%m-%d %H:00')
            
            if hour_key not in timeline:
                timeline[hour_key] = {
                    'hour': hour_key,
                    'count': 0,
                    'actions': {}
                }
            
            timeline[hour_key]['count'] += 1
            
            action = entry.get('action', 'unknown')
            timeline[hour_key]['actions'][action] = timeline[hour_key]['actions'].get(action, 0) + 1
        
        timeline_list = sorted(timeline.values(), key=lambda x: x['hour'], reverse=True)
        
        return success_response(
            data={
                "timeline": timeline_list,
                "hours": hours,
                "totalEntries": len(history)
            },
            message=f"Retrieved {hours}-hour activity timeline"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get hourly timeline: {e}")
        return error_response(str(e), 500)


# ============================================================================
# QUERY HISTORY (Separate from general history)
# ============================================================================

@router.get("/queries")
async def get_query_history(
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user)
):
    """
    Get query/question history
    
    - **limit**: Maximum queries to return
    - **skip**: Number to skip
    """
    try:
        queries = await get_queries_by_user(user_id, limit, skip)
        
        return success_response(
            data={"queries": queries, "count": len(queries)},
            message=f"Retrieved {len(queries)} queries"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get queries: {e}")
        return error_response(str(e), 500)


@router.get("/queries/recent")
async def get_recent_queries_route(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user)
):
    """
    Get recent queries
    
    - **limit**: Number of queries
    """
    try:
        queries = await get_recent_queries(user_id, limit)
        
        return success_response(
            data={"queries": queries, "count": len(queries)},
            message=f"Retrieved {len(queries)} recent queries"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get recent queries: {e}")
        return error_response(str(e), 500)


@router.get("/queries/stats")
async def get_query_statistics(
    user_id: str = Depends(get_current_user)
):
    """Get query statistics"""
    
    try:
        stats = await get_query_stats(user_id)
        
        return success_response(
            data=stats,
            message="Query statistics retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get query stats: {e}")
        return error_response(str(e), 500)


# ============================================================================
# ACTIVITY ANALYTICS
# ============================================================================

@router.get("/analytics/summary")
async def get_activity_summary(
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user)
):
    """
    Get comprehensive activity summary
    
    - **days**: Time period in days
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get history stats
        history_stats = await get_history_stats(user_id, start_date)
        
        # Get query stats
        query_stats = await get_query_stats(user_id)
        
        # Combine into summary
        summary = {
            "period": {
                "days": days,
                "startDate": start_date.isoformat(),
                "endDate": datetime.utcnow().isoformat()
            },
            "history": history_stats,
            "queries": query_stats,
            "totalActivity": history_stats.get('totalEntries', 0) + query_stats.get('totalQueries', 0)
        }
        
        return success_response(
            data=summary,
            message="Activity summary retrieved"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get activity summary: {e}")
        return error_response(str(e), 500)


@router.get("/analytics/popular-resources")
async def get_popular_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user)
):
    """
    Get most accessed resources
    
    - **resource_type**: Filter by type (video/document/chat)
    - **limit**: Number of results
    - **days**: Time period
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        history = await get_user_history(
            user_id=user_id,
            limit=1000,
            resource_type=resource_type,
            start_date=start_date
        )
        
        # Count resource access
        resource_counts = {}
        for entry in history:
            resource_id = entry.get('resourceId')
            res_type = entry.get('resourceType')
            
            if resource_id:
                key = f"{res_type}:{resource_id}"
                
                if key not in resource_counts:
                    resource_counts[key] = {
                        'resourceId': resource_id,
                        'resourceType': res_type,
                        'count': 0,
                        'lastAccessed': entry.get('createdAt')
                    }
                
                resource_counts[key]['count'] += 1
                
                # Update last accessed if more recent
                if entry.get('createdAt') > resource_counts[key]['lastAccessed']:
                    resource_counts[key]['lastAccessed'] = entry.get('createdAt')
        
        # Sort by count and limit
        popular = sorted(
            resource_counts.values(),
            key=lambda x: x['count'],
            reverse=True
        )[:limit]
        
        return success_response(
            data={
                "resources": popular,
                "count": len(popular),
                "period": days
            },
            message=f"Retrieved {len(popular)} popular resources"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get popular resources: {e}")
        return error_response(str(e), 500)


# ============================================================================
# EXPORT HISTORY
# ============================================================================

@router.get("/export")
async def export_history(
    format: str = Query("json", regex="^(json|csv)$"),
    days: Optional[int] = Query(None, ge=1, le=365),
    user_id: str = Depends(get_current_user)
):
    """
    Export user history
    
    - **format**: Export format (json/csv)
    - **days**: Optional - limit to last N days
    """
    try:
        from fastapi.responses import StreamingResponse
        import json
        import io
        
        # Get history
        start_date = None
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
        
        history = await get_user_history(
            user_id=user_id,
            limit=10000,
            start_date=start_date
        )
        
        if format == "json":
            # Export as JSON
            json_data = json.dumps(history, indent=2, default=str)
            
            return StreamingResponse(
                io.BytesIO(json_data.encode()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=history_{user_id}.json"
                }
            )
        
        else:
            # Export as CSV
            import csv
            
            output = io.StringIO()
            if history:
                writer = csv.DictWriter(output, fieldnames=history[0].keys())
                writer.writeheader()
                writer.writerows(history)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=history_{user_id}.csv"
                }
            )
        
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        return error_response(str(e), 500)
