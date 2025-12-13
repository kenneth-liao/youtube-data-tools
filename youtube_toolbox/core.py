import os
import re
import logging
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Configure logging
logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for interacting with YouTube API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is not set")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
    def parse_url(self, url: str) -> str:
        """
        Parse the URL to get the video ID
        """
        if not url:
            return ""
        # Handle full URLs
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        if video_id_match:
            return video_id_match.group(1)
        # Handle just the ID (11 chars)
        if re.match(r"^[0-9A-Za-z_-]{11}$", url):
            return url
        return url
    
    def normalize_region_code(self, region_code: str) -> str:
        """
        Convert region codes to valid ISO 3166-1 alpha-2 country codes
        """
        if not region_code:
            return None
            
        # Common mappings for non-standard codes to standard ISO codes
        region_mapping = {
            'KO': 'KR',  # Korea
            'EN': 'US',  # English -> US as fallback
            'JP': 'JP',  # Japan
            'CN': 'CN',  # China
        }
        
        # Convert to uppercase
        region_code = region_code.upper()
        
        # Return mapped code or original if no mapping exists
        return region_mapping.get(region_code, region_code)
    
    def search_videos(self, query: str, max_results: int = 10, **options) -> Dict[str, Any]:
        """
        Search for YouTube videos based on query and options
        """
        try:
            search_params = {
                'part': 'snippet',
                'q': query,
                'maxResults': max_results,
                'type': options.get('type', 'video')
            }
            
            # Add optional parameters if provided
            for param in ['channelId', 'order', 'videoDuration', 'publishedAfter', 
                        'publishedBefore', 'videoCaption', 'videoDefinition', 'regionCode']:
                if param in options and options[param]:
                    search_params[param] = options[param]
            
            response = self.youtube.search().list(**search_params).execute()
            return response
        except HttpError as e:
            logger.error(f"Error searching videos: {e}")
            raise e
    
    def get_video_details(self, video_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific YouTube video
        """
        video_id = self.parse_url(video_id)
        
        try:
            response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            ).execute()
            return response
        except HttpError as e:
            logger.error(f"Error getting video details: {e}")
            raise e
    
    def get_channel_details(self, channel_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific YouTube channel
        """
        channel_id = self.parse_url(channel_id)
        
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            ).execute()
            return response
        except HttpError as e:
            logger.error(f"Error getting channel details: {e}")
            raise e
    
    def get_video_comments(self, video_id: str, max_results: int = 20, **options) -> Dict[str, Any]:
        """
        Get comments for a specific YouTube video
        """
        video_id = self.parse_url(video_id)
        
        try:
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': max_results
            }
            
            if 'order' in options:
                params['order'] = options['order']
                
            if 'pageToken' in options:
                params['pageToken'] = options['pageToken']
                
            if options.get('includeReplies'):
                params['part'] = 'snippet,replies'
                
            response = self.youtube.commentThreads().list(**params).execute()
            return response
        except HttpError as e:
            logger.error(f"Error getting comments: {e}")
            raise e
    
    def get_video_transcript(self, video_id: str, language: Optional[str] = 'ko') -> List[Dict[str, Any]]:
        """
        Get transcript for a specific YouTube video
        """
        video_id = self.parse_url(video_id)
        
        try:
            # Instantiate the API client
            yt_transcript_api = YouTubeTranscriptApi()

            if language:
                transcript_list = yt_transcript_api.list(video_id)
                try:
                    transcript = transcript_list.find_transcript([language])
                    return transcript.fetch()
                except NoTranscriptFound:
                    # Fallback to generated transcript if available
                    try:
                        transcript = transcript_list.find_generated_transcript([language])
                        return transcript.fetch()
                    except:
                        # Final fallback to any available transcript
                        transcript = transcript_list.find_transcript(['en'])
                        return transcript.fetch()
            else:
                return yt_transcript_api.fetch(video_id)
                
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.error(f"No transcript available for video {video_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting transcript for video {video_id}: {e}")
            raise e

    def get_related_videos(self, video_id: str, max_results: Optional[int] = 10) -> Dict[str, Any]:
        """
        Get related videos for a specific YouTube video
        """
        video_id = self.parse_url(video_id)
        
        try:
            # Use search to find videos for a similar query to effectively get related content
            # First, get video details to use title for search
            video_details = self.get_video_details(video_id)
            if not video_details.get('items'):
                raise ValueError(f"Video with ID {video_id} not found")
            
            video_title = video_details['items'][0]['snippet']['title']
            # Extract a few keywords from the title for search
            search_query = ' '.join(video_title.split()[:3]) if video_title else ''
            
            # Search for videos with similar content
            response = self.youtube.search().list(
                part='snippet',
                q=search_query,
                type='video',
                maxResults=max_results,
                videoCategoryId=video_details['items'][0]['snippet'].get('categoryId', ''),
                relevanceLanguage='en'  # Can be adjusted based on requirements
            ).execute()
            
            # Filter out the original video from results
            if 'items' in response:
                response['items'] = [item for item in response['items'] 
                                    if item.get('id', {}).get('videoId') != video_id]
                # Adjust result count if original video was filtered
                if len(response['items']) < max_results:
                    response['pageInfo']['totalResults'] = len(response['items'])
                    response['pageInfo']['resultsPerPage'] = len(response['items'])
            
            # Add the search query to the response for reference
            response['searchQuery'] = search_query
            
            return response
        except HttpError as e:
            logger.error(f"Error getting related videos: {e}")
            raise e
          
            
    def get_trending_videos(self, region_code: Optional[str] = 'ko', max_results: Optional[int] = 5) -> Dict[str, Any]:
        """
        Get trending videos for a specific region
        """
        try:
            params = {
                'part': 'snippet,contentDetails,statistics',
                'chart': 'mostPopular',
                'maxResults': max_results
            }
            
            if region_code:
                # Normalize region code to ensure valid ISO country code format
                normalized_code = self.normalize_region_code(region_code)
                params['regionCode'] = normalized_code
                
            response = self.youtube.videos().list(**params).execute()
            return response
        except HttpError as e:
            logger.error(f"Error getting trending videos: {e}")
            raise e
            
    def format_time(self, milliseconds: int) -> str:
        """
        Format milliseconds into a human-readable time string
        """
        seconds = int(milliseconds / 1000)
        minutes = int(seconds / 60)
        hours = int(minutes / 60)
        
        remaining_seconds = seconds % 60
        remaining_minutes = minutes % 60
        
        if hours > 0:
            return f"{hours:02d}:{remaining_minutes:02d}:{remaining_seconds:02d}"
        else:
            return f"{remaining_minutes:02d}:{remaining_seconds:02d}"

    def get_video_enhanced_transcript(self, video_ids: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get enhanced transcript for one or more YouTube videos with advanced filtering and processing
        """
        result = {
            "videos": [],
            "status": {
                "success": True,
                "message": "Transcripts processed successfully",
                "failedCount": 0,
                "successCount": 0
            }
        }
        
        # Process options
        language = options.get('language')
        format_type = options.get('format', 'timestamped')
        include_metadata = options.get('includeMetadata', False)
        time_range = options.get('timeRange')
        search_filter = options.get('search')
        segment_options = options.get('segment')
        
        # Process each video
        for video_id in video_ids:
            video_result = {"videoId": video_id}
            
            try:
                # Get video details if metadata requested
                if include_metadata:
                    video_data = self.get_video_details(video_id)
                    if not video_data.get('items'):
                        video_result["error"] = f"Video with ID {video_id} not found"
                        result["videos"].append(video_result)
                        result["status"]["failedCount"] += 1
                        continue
                        
                    video = video_data['items'][0]
                    video_result["metadata"] = {
                        'id': video.get('id'),
                        'title': video.get('snippet', {}).get('title'),
                        'channelTitle': video.get('snippet', {}).get('channelTitle'),
                        'publishedAt': video.get('snippet', {}).get('publishedAt'),
                        'duration': video.get('contentDetails', {}).get('duration')
                    }
                
                # Call the get_video_transcript method which returns transcript data
                raw_transcript_data = self.get_video_transcript(video_id, language)
                
                # Check if transcript was fetched successfully
                if not raw_transcript_data or (isinstance(raw_transcript_data, dict) and 'error' in raw_transcript_data):
                    error_msg = raw_transcript_data.get('error', "Failed to retrieve transcript") if isinstance(raw_transcript_data, dict) else "Failed to retrieve transcript"
                    video_result["error"] = error_msg
                    result["videos"].append(video_result)
                    result["status"]["failedCount"] += 1
                    continue
                
                # Get transcript segments - adapt to different response formats
                if isinstance(raw_transcript_data, dict) and 'transcript' in raw_transcript_data:
                    # If it's a dictionary with transcript key (from existing get_video_transcript method)
                    segments = raw_transcript_data['transcript']
                elif isinstance(raw_transcript_data, dict) and 'text' in raw_transcript_data:
                    # If the get_video_transcript method returned a formatted response with 'text'
                    # This is a fallback case
                    segments = []
                    video_result["error"] = "Transcript format not supported"
                    result["videos"].append(video_result)
                    result["status"]["failedCount"] += 1
                    continue
                elif isinstance(raw_transcript_data, list):
                    # If it returned a list directly (might happen in some cases)
                    segments = []
                    for item in raw_transcript_data:
                        segments.append({
                            'text': item.get('text', ''),
                            'start': item.get('start', 0),
                            'duration': item.get('duration', 0),
                            'timestamp': self.format_time(int(item.get('start', 0) * 1000))
                        })
                else:
                    # This handles the FetchedTranscript objects from YouTubeTranscriptApi
                    # that don't have a .get() method
                    segments = []
                    for segment in raw_transcript_data:
                        text = getattr(segment, 'text', '')
                        start = getattr(segment, 'start', 0)
                        duration = getattr(segment, 'duration', 0)
                        
                        segments.append({
                            'text': text,
                            'start': start,
                            'duration': duration,
                            'timestamp': self.format_time(int(start * 1000))
                        })
                
                # Apply time range filter if specified
                if time_range:
                    start_time = time_range.get('start')
                    end_time = time_range.get('end')
                    
                    if start_time is not None:
                        segments = [s for s in segments if (s['start'] + s['duration']) >= start_time]
                    
                    if end_time is not None:
                        segments = [s for s in segments if s['start'] <= end_time]
                
                # Apply search filter if specified
                if search_filter and segments:
                    query = search_filter.get('query', '')
                    case_sensitive = search_filter.get('caseSensitive', False)
                    context_lines = search_filter.get('contextLines', 0)
                    
                    if query:
                        # Search in segments
                        matched_indices = []
                        search_query = query if case_sensitive else query.lower()
                        
                        for i, segment in enumerate(segments):
                            text = segment['text'] if case_sensitive else segment['text'].lower()
                            if search_query in text:
                                matched_indices.append(i)
                        
                        # Include context lines
                        if context_lines > 0:
                            expanded_indices = set()
                            for idx in matched_indices:
                                # Add the context lines before and after
                                for i in range(max(0, idx - context_lines), min(len(segments), idx + context_lines + 1)):
                                    expanded_indices.add(i)
                            
                            matched_indices = sorted(expanded_indices)
                        
                        # Filter segments by matched indices
                        segments = [segments[i] for i in matched_indices]
                
                # Apply segmentation if specified
                if segment_options and segments:
                    method = segment_options.get('method', 'equal')
                    count = segment_options.get('count', 1)
                    
                    if method == 'equal' and count > 1:
                        # Divide into equal parts
                        segment_size = len(segments) // count
                        segmented_transcript = []
                        
                        for i in range(count):
                            start_idx = i * segment_size
                            end_idx = start_idx + segment_size if i < count - 1 else len(segments)
                            
                            segment_chunks = segments[start_idx:end_idx]
                            if segment_chunks:  # Only add non-empty segments
                                segmented_transcript.append({
                                    "index": i,
                                    "segments": segment_chunks,
                                    "text": " ".join([s['text'] for s in segment_chunks])
                                })
                        
                        video_result["segments"] = segmented_transcript
                    elif method == 'smart' and count > 1:
                        # Use a smarter segmentation approach
                        # For simplicity, we'll use a basic approach dividing by total character count
                        total_text = " ".join([s['text'] for s in segments])
                        total_chars = len(total_text)
                        chars_per_segment = total_chars // count
                        
                        segmented_transcript = []
                        current_segment = []
                        current_chars = 0
                        segment_idx = 0
                        
                        for s in segments:
                            current_segment.append(s)
                            current_chars += len(s['text'])
                            
                            if current_chars >= chars_per_segment and segment_idx < count - 1:
                                segmented_transcript.append({
                                    "index": segment_idx,
                                    "segments": current_segment,
                                    "text": " ".join([seg['text'] for seg in current_segment])
                                })
                                segment_idx += 1
                                current_segment = []
                                current_chars = 0
                        
                        # Add the last segment if not empty
                        if current_segment:
                            segmented_transcript.append({
                                "index": segment_idx,
                                "segments": current_segment,
                                "text": " ".join([seg['text'] for seg in current_segment])
                            })
                        
                        video_result["segments"] = segmented_transcript
                
                # Format transcript based on format type
                if format_type == 'raw':
                    video_result["transcript"] = segments
                elif format_type == 'timestamped':
                    video_result["transcript"] = [
                        f"[{s['timestamp']}] {s['text']}" for s in segments
                    ]
                elif format_type == 'merged':
                    video_result["transcript"] = " ".join([s['text'] for s in segments])
                
                # Store statistics
                video_result["statistics"] = {
                    "segmentCount": len(segments),
                    "totalDuration": sum([s['duration'] for s in segments]),
                    "averageSegmentLength": sum([len(s['text']) for s in segments]) / len(segments) if segments else 0
                }
                
                result["videos"].append(video_result)
                result["status"]["successCount"] += 1
                
            except Exception as e:
                logger.exception(f"Error processing transcript for video {video_id}: {e}")
                video_result["error"] = str(e)
                result["videos"].append(video_result)
                result["status"]["failedCount"] += 1
        
        # Update overall status
        if result["status"]["failedCount"] > 0:
            if result["status"]["successCount"] == 0:
                result["status"]["success"] = False
                result["status"]["message"] = "All transcript requests failed"
            else:
                result["status"]["message"] = f"Partially successful ({result['status']['failedCount']} failed, {result['status']['successCount']} succeeded)"
        
        return result
