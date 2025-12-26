# services/async_processor.py - FASTAPI ASYNC VIDEO PROCESSOR
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import traceback

from config.logging_config import logger
from config.settings import settings


# ============================================================================
# ASYNC VIDEO PROCESSOR
# ============================================================================

class AsyncVideoProcessor:
    """Async video processing with thread/process pools"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=max_workers)
    
    async def process_single_video(
        self,
        url: str,
        user_id: str,
        process_func: Callable,
        use_process_pool: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single video asynchronously
        
        Args:
            url: YouTube video URL
            user_id: User ID
            process_func: Processing function to execute
            use_process_pool: Use ProcessPoolExecutor instead of ThreadPoolExecutor
        
        Returns:
            Dictionary with processing results
        """
        try:
            start_time = datetime.utcnow()
            logger.info(f"🎬 Starting video processing: {url}")
            
            loop = asyncio.get_event_loop()
            executor = self.process_executor if use_process_pool else self.thread_executor
            
            # Run blocking function in executor
            result = await loop.run_in_executor(
                executor,
                process_func,
                url,
                user_id
            )
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Video processing completed in {duration:.2f}s: {url}")
            
            return {
                'success': True,
                'url': url,
                'userId': user_id,
                'result': result,
                'duration': duration,
                'completedAt': end_time
            }
            
        except Exception as e:
            logger.error(f"❌ Video processing failed for {url}: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'url': url,
                'userId': user_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    async def process_multiple_videos(
        self,
        urls: List[str],
        user_id: str,
        process_func: Callable,
        use_process_pool: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Process multiple videos concurrently
        
        Args:
            urls: List of YouTube video URLs
            user_id: User ID
            process_func: Processing function to execute
            use_process_pool: Use ProcessPoolExecutor instead of ThreadPoolExecutor
        
        Returns:
            List of processing results
        """
        try:
            logger.info(f"🎬 Starting batch processing of {len(urls)} videos")
            
            # Create tasks for all videos
            tasks = [
                self.process_single_video(url, user_id, process_func, use_process_pool)
                for url in urls
            ]
            
            # Process all videos concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and failures
            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            failed = len(results) - successful
            
            logger.info(f"✅ Batch processing completed: {successful} successful, {failed} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {str(e)}")
            return []
    
    async def process_with_callback(
        self,
        url: str,
        user_id: str,
        process_func: Callable,
        callback_func: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process video with callback on completion
        
        Args:
            url: YouTube video URL
            user_id: User ID
            process_func: Processing function
            callback_func: Callback function to execute after processing
        
        Returns:
            Processing result
        """
        try:
            result = await self.process_single_video(url, user_id, process_func)
            
            # Execute callback if provided
            if callback_func and result.get('success'):
                try:
                    await asyncio.to_thread(callback_func, result)
                except Exception as e:
                    logger.error(f"❌ Callback failed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Processing with callback failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_with_timeout(
        self,
        url: str,
        user_id: str,
        process_func: Callable,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Process video with timeout
        
        Args:
            url: YouTube video URL
            user_id: User ID
            process_func: Processing function
            timeout: Timeout in seconds (default: 5 minutes)
        
        Returns:
            Processing result
        """
        try:
            result = await asyncio.wait_for(
                self.process_single_video(url, user_id, process_func),
                timeout=timeout
            )
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"⏱️  Video processing timed out after {timeout}s: {url}")
            return {
                'success': False,
                'url': url,
                'error': f'Processing timed out after {timeout} seconds'
            }
        except Exception as e:
            logger.error(f"❌ Processing with timeout failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_batch_with_progress(
        self,
        urls: List[str],
        user_id: str,
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple videos with progress tracking
        
        Args:
            urls: List of YouTube video URLs
            user_id: User ID
            process_func: Processing function
            progress_callback: Callback function for progress updates
        
        Returns:
            List of processing results
        """
        try:
            results = []
            total = len(urls)
            
            for idx, url in enumerate(urls, 1):
                result = await self.process_single_video(url, user_id, process_func)
                results.append(result)
                
                # Report progress
                progress = (idx / total) * 100
                logger.info(f"📊 Progress: {idx}/{total} ({progress:.1f}%)")
                
                # Execute progress callback
                if progress_callback:
                    try:
                        await asyncio.to_thread(
                            progress_callback,
                            {
                                'current': idx,
                                'total': total,
                                'progress': progress,
                                'lastResult': result
                            }
                        )
                    except Exception as e:
                        logger.error(f"❌ Progress callback failed: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Batch processing with progress failed: {e}")
            return []
    
    async def process_with_retry(
        self,
        url: str,
        user_id: str,
        process_func: Callable,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Dict[str, Any]:
        """
        Process video with automatic retry on failure
        
        Args:
            url: YouTube video URL
            user_id: User ID
            process_func: Processing function
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            Processing result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Processing attempt {attempt + 1}/{max_retries}: {url}")
                
                result = await self.process_single_video(url, user_id, process_func)
                
                if result.get('success'):
                    if attempt > 0:
                        logger.info(f"✅ Processing succeeded on retry {attempt + 1}")
                    return result
                
                last_error = result.get('error', 'Unknown error')
                
                # Wait before retry
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️  Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
        
        logger.error(f"❌ All {max_retries} attempts failed for {url}")
        return {
            'success': False,
            'url': url,
            'error': f'Failed after {max_retries} attempts: {last_error}'
        }
    
    def shutdown(self):
        """Shutdown executors"""
        logger.info("🛑 Shutting down async processor executors...")
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        logger.info("✅ Executors shutdown complete")


# ============================================================================
# GLOBAL PROCESSOR INSTANCE
# ============================================================================

async_processor = AsyncVideoProcessor(max_workers=3)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def process_multiple_videos(
    urls: List[str],
    user_id: str,
    process_func: Callable
) -> List[Dict[str, Any]]:
    """
    Process multiple videos concurrently (convenience function)
    
    Args:
        urls: List of YouTube video URLs
        user_id: User ID
        process_func: Processing function to execute
    
    Returns:
        List of processing results
    """
    return await async_processor.process_multiple_videos(urls, user_id, process_func)


async def process_video_with_retry(
    url: str,
    user_id: str,
    process_func: Callable,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Process single video with retry (convenience function)
    
    Args:
        url: YouTube video URL
        user_id: User ID
        process_func: Processing function
        max_retries: Maximum retry attempts
    
    Returns:
        Processing result
    """
    return await async_processor.process_with_retry(url, user_id, process_func, max_retries)


async def process_video_with_timeout(
    url: str,
    user_id: str,
    process_func: Callable,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Process video with timeout (convenience function)
    
    Args:
        url: YouTube video URL
        user_id: User ID
        process_func: Processing function
        timeout: Timeout in seconds
    
    Returns:
        Processing result
    """
    return await async_processor.process_with_timeout(url, user_id, process_func, timeout)


# ============================================================================
# TASK QUEUE (For Background Tasks)
# ============================================================================

class TaskQueue:
    """Simple async task queue for background processing"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: Dict[str, Any] = {}
        self.is_running = False
    
    async def add_task(
        self,
        task_id: str,
        url: str,
        user_id: str,
        process_func: Callable
    ):
        """Add task to queue"""
        await self.queue.put({
            'task_id': task_id,
            'url': url,
            'user_id': user_id,
            'process_func': process_func,
            'created_at': datetime.utcnow()
        })
        logger.info(f"📥 Task added to queue: {task_id}")
    
    async def process_queue(self):
        """Process tasks from queue"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Get task from queue
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                task_id = task['task_id']
                logger.info(f"🔄 Processing task: {task_id}")
                
                # Process video
                result = await async_processor.process_single_video(
                    task['url'],
                    task['user_id'],
                    task['process_func']
                )
                
                # Store result
                self.results[task_id] = result
                
                # Mark task as done
                self.queue.task_done()
                
                logger.info(f"✅ Task completed: {task_id}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Task processing error: {e}")
    
    async def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result for a task"""
        return self.results.get(task_id)
    
    def stop(self):
        """Stop processing queue"""
        self.is_running = False
        logger.info("🛑 Task queue stopped")


# Global task queue instance
task_queue = TaskQueue()


# ============================================================================
# BACKGROUND TASK HELPERS
# ============================================================================

async def start_background_task(
    task_id: str,
    url: str,
    user_id: str,
    process_func: Callable
):
    """
    Start a background processing task
    
    Args:
        task_id: Unique task ID
        url: YouTube video URL
        user_id: User ID
        process_func: Processing function
    """
    await task_queue.add_task(task_id, url, user_id, process_func)


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a background task
    
    Args:
        task_id: Task ID
    
    Returns:
        Task status dictionary
    """
    result = await task_queue.get_result(task_id)
    
    if result:
        return {
            'status': 'completed' if result.get('success') else 'failed',
            'result': result
        }
    else:
        return {
            'status': 'pending',
            'message': 'Task is still processing or not found'
        }


# ============================================================================
# RATE LIMITER FOR CONCURRENT PROCESSING
# ============================================================================

class RateLimiter:
    """Rate limiter for concurrent API calls"""
    
    def __init__(self, max_concurrent: int = 3, rate_per_minute: int = 60):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_per_minute = rate_per_minute
        self.request_times: List[float] = []
    
    async def acquire(self):
        """Acquire rate limit permission"""
        async with self.semaphore:
            # Clean old request times
            current_time = asyncio.get_event_loop().time()
            self.request_times = [
                t for t in self.request_times
                if current_time - t < 60
            ]
            
            # Check rate limit
            if len(self.request_times) >= self.rate_per_minute:
                wait_time = 60 - (current_time - self.request_times[0])
                logger.warning(f"⏳ Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            
            # Record request time
            self.request_times.append(current_time)
            
            yield


# Global rate limiter
rate_limiter = RateLimiter(max_concurrent=3, rate_per_minute=60)
