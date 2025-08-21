#!/usr/bin/env python3
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
from fastmcp import FastMCP

# Load configuration (TODO: read from file)
config = {
  "backend_url": "http://localhost:3001",
  "default_entity_id": "1",
  "timeout_seconds": 30
}

mcp = FastMCP("Reservo MCP")

class ReservationClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    async def get_reservations(self, entity_id: str, year: int, month: int) -> List[Dict[str, Any]]:
        """Get reservations for a specific month"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/api/entities/{entity_id}/reservations?year={year}&month={month}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', []) if data.get('success') else []
                return []

client = ReservationClient(config['backend_url'])

@mcp.tool()
async def check_date_availability(entity_id: str, date: str) -> Dict[str, Any]:
    """
    Check if a specific date is available for booking.
    
    Args:
        entity_id: ID of the entity to check
        date: Date to check in YYYY-MM-DD format
    
    Returns:
        Dictionary with availability status and reservation details if occupied
    """
    try:
        check_date = datetime.strptime(date, '%Y-%m-%d')
        year = check_date.year
        month = check_date.month
        
        reservations = await client.get_reservations(entity_id, year, month)
        
        # Check if date falls within any reservation
        for reservation in reservations:
            start_date = datetime.fromisoformat(reservation['startDate'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(reservation['endDate'].replace('Z', '+00:00'))
            
            if start_date.date() <= check_date.date() < end_date.date():
                return {
                    'available': False,
                    'date': date,
                    'entity_id': entity_id,
                    'reservation': {
                        'id': reservation['reservationId'],
                        'booked_by': reservation['bookedBy'],
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d'),
                        'created_at': reservation['createdAt']
                    }
                }
        
        return {
            'available': True,
            'date': date,
            'entity_id': entity_id,
            'message': f'Entity {entity_id} is available on {date}'
        }
        
    except ValueError as e:
        return {
            'error': f'Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Failed to check availability: {str(e)}'
        }

@mcp.tool()
async def check_date_range_availability(entity_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Check availability for a date range and provide detailed information about conflicts.
    
    Args:
        entity_id: ID of the entity to check
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with availability status, conflicts, and available periods
    """
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt >= end_dt:
            return {'error': 'Start date must be before end date'}
        
        # Get reservations for all months in the range
        months_to_check = set()
        current = start_dt.replace(day=1)
        while current <= end_dt:
            months_to_check.add((current.year, current.month))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        all_reservations = []
        for year, month in months_to_check:
            reservations = await client.get_reservations(entity_id, year, month)
            all_reservations.extend(reservations)
        
        # Find conflicts
        conflicts = []
        for reservation in all_reservations:
            res_start = datetime.fromisoformat(reservation['startDate'].replace('Z', '+00:00')).date()
            res_end = datetime.fromisoformat(reservation['endDate'].replace('Z', '+00:00')).date()
            
            # Check for overlap: start < res_end AND end > res_start
            if start_dt.date() < res_end and end_dt.date() > res_start:
                conflicts.append({
                    'id': reservation['reservationId'],
                    'booked_by': reservation['bookedBy'],
                    'start_date': res_start.strftime('%Y-%m-%d'),
                    'end_date': res_end.strftime('%Y-%m-%d'),
                    'created_at': reservation['createdAt']
                })
        
        if not conflicts:
            return {
                'available': True,
                'entity_id': entity_id,
                'requested_period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'message': f'Entity {entity_id} is completely available from {start_date} to {end_date}'
            }
        
        # Find available periods within the requested range
        available_periods = []
        current_date = start_dt.date()
        
        while current_date < end_dt.date():
            # Check if current_date is free
            is_free = True
            blocking_reservation = None
            
            for conflict in conflicts:
                conflict_start = datetime.strptime(conflict['start_date'], '%Y-%m-%d').date()
                conflict_end = datetime.strptime(conflict['end_date'], '%Y-%m-%d').date()
                
                if conflict_start <= current_date < conflict_end:
                    is_free = False
                    blocking_reservation = conflict
                    break
            
            if is_free:
                # Find the end of this available period
                period_end = current_date
                while period_end < end_dt.date():
                    next_day = period_end + timedelta(days=1)
                    is_next_free = True
                    
                    for conflict in conflicts:
                        conflict_start = datetime.strptime(conflict['start_date'], '%Y-%m-%d').date()
                        conflict_end = datetime.strptime(conflict['end_date'], '%Y-%m-%d').date()
                        
                        if conflict_start <= next_day < conflict_end:
                            is_next_free = False
                            break
                    
                    if is_next_free:
                        period_end = next_day
                    else:
                        break
                
                available_periods.append({
                    'start_date': current_date.strftime('%Y-%m-%d'),
                    'end_date': period_end.strftime('%Y-%m-%d')
                })
                
                current_date = period_end + timedelta(days=1)
            else:
                # Skip to the end of the blocking reservation
                conflict_end = datetime.strptime(blocking_reservation['end_date'], '%Y-%m-%d').date()
                current_date = conflict_end
        
        return {
            'available': False,
            'entity_id': entity_id,
            'requested_period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'conflicts': conflicts,
            'available_periods': available_periods,
            'message': f'Entity {entity_id} has {len(conflicts)} conflicting reservation(s) in the requested period'
        }
        
    except ValueError as e:
        return {
            'error': f'Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Failed to check availability: {str(e)}'
        }

if __name__ == "__main__":
    mcp.run()
