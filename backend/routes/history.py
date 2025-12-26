# backend/routes/history.py - HISTORY/ACTIVITY ENDPOINT

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from middleware.auth import get_current_user
from database.database import get_db
from config.logging_config import logger

router = APIRouter(prefix="/api/history", tags=["History"])

# ============================================================================
# GET USER ACTIVITIES
# ============================================================================

@router.get("/")
async def get_user_activities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get user activity history
    
    Activity types: chat, document, video, auth
    """
    try:
        logger.info(f"📜 Getting activities for user: {user_id}")
        
        # Build query
        query = {"user_id": user_id}
        if activity_type:
            query["activity_type"] = activity_type
        
        # Get total count
        total = db.activities.count_documents(query)
        
        # Get activities with pagination
        skip = (page - 1) * page_size
        activities_cursor = db.activities.find(query).sort("timestamp", -1).skip(skip).limit(page_size)
        
        activities = []
        for activity in activities_cursor:
            activities.append({
                "activity_id": str(activity["_id"]),
                "activity_type": activity.get("activity_type", "general"),
                "action": activity.get("action", ""),
                "resource_type": activity.get("resource_type", ""),
                "resource_id": activity.get("resource_id", ""),
                "message": activity.get("message", ""),
                "metadata": activity.get("metadata", {}),
                "timestamp": activity.get("timestamp", datetime.utcnow().timestamp()),
            })
        
        logger.info(f"✅ Retrieved {len(activities)} activities (page {page}/{(total + page_size - 1) // page_size})")
        
        return {
            "success": True,
            "activities": activities,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activities: {str(e)}"
        )


# ============================================================================
# CLEAR USER HISTORY
# ============================================================================

@router.delete("/")
async def clear_user_history(
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Clear all user activity history
    """
    try:
        logger.info(f"🗑️ Clearing history for user: {user_id}")
        
        result = db.activities.delete_many({"user_id": user_id})
        
        logger.info(f"✅ Deleted {result.deleted_count} activities")
        
        return {
            "success": True,
            "message": f"Deleted {result.deleted_count} activities",
            "deleted_count": result.deleted_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )


# ============================================================================
# GET ACTIVITIES BY DATE RANGE
# ============================================================================

@router.get("/range")
async def get_activities_by_date_range(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get activities within a date range
    """
    try:
        logger.info(f"📅 Getting activities for date range: {start_date} to {end_date}")
        
        # Build query
        query = {"user_id": user_id}
        
        if start_date or end_date:
            query["timestamp"] = {}
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query["timestamp"]["$gte"] = start_dt.timestamp()
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query["timestamp"]["$lte"] = end_dt.timestamp()
        
        # Get activities
        activities_cursor = db.activities.find(query).sort("timestamp", -1)
        
        activities = []
        for activity in activities_cursor:
            activities.append({
                "activity_id": str(activity["_id"]),
                "activity_type": activity.get("activity_type", "general"),
                "action": activity.get("action", ""),
                "resource_type": activity.get("resource_type", ""),
                "resource_id": activity.get("resource_id", ""),
                "message": activity.get("message", ""),
                "timestamp": activity.get("timestamp", datetime.utcnow().timestamp()),
            })
        
        logger.info(f"✅ Retrieved {len(activities)} activities for date range")
        
        return {
            "success": True,
            "activities": activities,
            "total": len(activities),
            "start_date": start_date,
            "end_date": end_date
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting activities by date: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activities: {str(e)}"
        )


# ============================================================================
# GET ACTIVITY STATS
# ============================================================================

@router.get("/stats")
async def get_activity_stats(
    user_id: str = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get user activity statistics
    """
    try:
        logger.info(f"📊 Getting activity stats for user: {user_id}")
        
        # Get total activities
        total_activities = db.activities.count_documents({"user_id": user_id})
        
        # Get activities by type
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$activity_type",
                "count": {"$sum": 1}
            }}
        ]
        
        activities_by_type = {}
        for result in db.activities.aggregate(pipeline):
            activities_by_type[result["_id"]] = result["count"]
        
        # Get recent activities (last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).timestamp()
        recent_activities = db.activities.count_documents({
            "user_id": user_id,
            "timestamp": {"$gte": seven_days_ago}
        })
        
        stats = {
            "total_activities": total_activities,
            "activities_by_type": activities_by_type,
            "recent_activities_7days": recent_activities,
        }
        
        logger.info(f"✅ Activity stats retrieved: {stats}")
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting activity stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity stats: {str(e)}"
        )
