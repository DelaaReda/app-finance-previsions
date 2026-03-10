"""
Versioned Notes System
Implements versioned notes for tracking thesis evolution over time as required by V1
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum


class NoteType(Enum):
    THESIS = "thesis"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    ALERT = "alert"
    BRIEF = "brief"


@dataclass
class NoteVersion:
    version_id: str
    content: str
    author: str
    timestamp: str
    summary: str
    tags: List[str]
    references: List[str]  # Links, sources, etc.
    version_number: int


@dataclass
class Note:
    note_id: str
    title: str
    type: NoteType
    ticker: Optional[str]
    sector: Optional[str]
    created_at: str
    updated_at: str
    current_version: int
    versions: List[NoteVersion]
    status: str  # active, archived, deprecated
    related_notes: List[str]  # IDs of related notes
    metadata: Dict[str, Any]

    def to_dict(self):
        result = asdict(self)
        result['type'] = self.type.value
        return result


class VersionedNotesStore:
    """Store for versioned notes with thesis tracking capabilities."""
    
    def __init__(self, storage_dir: str = "data/notes"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.notes_file = self.storage_dir / "notes.jsonl"
        self.versions_file = self.storage_dir / "versions.jsonl"
        
        # Create files if they don't exist
        self.notes_file.touch(exist_ok=True)
    
    def _generate_id(self, content: str, suffix: str = "") -> str:
        """Generate unique ID for notes and versions."""
        content_hash = hashlib.sha256((content + suffix + datetime.utcnow().isoformat()).encode()).hexdigest()
        return content_hash[:16]
    
    def create_note(self, title: str, content: str, author: str, 
                   note_type: NoteType, ticker: Optional[str] = None,
                   sector: Optional[str] = None, summary: str = "",
                   tags: List[str] = None, references: List[str] = None) -> str:
        """Create a new note with initial version."""
        note_id = self._generate_id(f"{title}{content}{author}")
        
        # Create first version
        version = NoteVersion(
            version_id=self._generate_id(f"{note_id}_v1", "version"),
            content=content,
            author=author,
            timestamp=datetime.utcnow().isoformat(),
            summary=summary or title[:100],  # Use title as summary if not provided
            tags=tags or [],
            references=references or [],
            version_number=1
        )
        
        # Create note
        note = Note(
            note_id=note_id,
            title=title,
            type=note_type,
            ticker=ticker,
            sector=sector,
            created_at=version.timestamp,
            updated_at=version.timestamp,
            current_version=1,
            versions=[version],
            status="active",
            related_notes=[],
            metadata={}
        )
        
        # Save to storage
        with open(self.notes_file, "a") as f:
            f.write(json.dumps(note.to_dict()) + "\n")
        
        return note_id
    
    def update_note(self, note_id: str, new_content: str, author: str,
                   summary: str = "", tags: List[str] = None,
                   references: List[str] = None, status: str = None) -> bool:
        """Update an existing note by creating a new version."""
        # Read all notes to find the one to update
        notes = []
        target_note = None
        target_line_num = -1
        
        with open(self.notes_file, "r") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                note_data = json.loads(line)
                if note_data['note_id'] == note_id:
                    target_note = Note(
                        note_id=note_data['note_id'],
                        title=note_data['title'],
                        type=NoteType(note_data['type']),
                        ticker=note_data.get('ticker'),
                        sector=note_data.get('sector'),
                        created_at=note_data['created_at'],
                        updated_at=note_data['updated_at'],
                        current_version=note_data['current_version'],
                        versions=[NoteVersion(**v) for v in note_data['versions']],
                        status=note_data['status'],
                        related_notes=note_data['related_notes'],
                        metadata=note_data.get('metadata', {})
                    )
                    target_line_num = i
                notes.append(note_data)
        
        if not target_note:
            return False
        
        # Create new version
        new_version_num = target_note.current_version + 1
        new_version = NoteVersion(
            version_id=self._generate_id(f"{note_id}_v{new_version_num}", "version"),
            content=new_content,
            author=author,
            timestamp=datetime.utcnow().isoformat(),
            summary=summary or f"Version {new_version_num}",
            tags=tags or target_note.versions[-1].tags,  # Keep old tags if not specified
            references=references or [],
            version_number=new_version_num
        )
        
        # Update the note
        target_note.versions.append(new_version)
        target_note.current_version = new_version_num
        target_note.updated_at = new_version.timestamp
        if status:
            target_note.status = status
        
        # Write back all notes (replace the updated one)
        with open(self.notes_file, "w") as f:
            for i, note_data in enumerate(notes):
                if i == target_line_num:
                    # Write updated note
                    f.write(json.dumps(target_note.to_dict()) + "\n")
                else:
                    f.write(json.dumps(note_data) + "\n")
        
        return True
    
    def get_note(self, note_id: str, version: Optional[int] = None) -> Optional[Note]:
        """Get a specific note or a specific version of a note."""
        with open(self.notes_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                note_data = json.loads(line)
                if note_data['note_id'] == note_id:
                    note = Note(
                        note_id=note_data['note_id'],
                        title=note_data['title'],
                        type=NoteType(note_data['type']),
                        ticker=note_data.get('ticker'),
                        sector=note_data.get('sector'),
                        created_at=note_data['created_at'],
                        updated_at=note_data['updated_at'],
                        current_version=note_data['current_version'],
                        versions=[NoteVersion(**v) for v in note_data['versions']],
                        status=note_data['status'],
                        related_notes=note_data['related_notes'],
                        metadata=note_data.get('metadata', {})
                    )
                    
                    # If specific version requested, return only that version content
                    if version is not None:
                        matching_version = None
                        for v in note.versions:
                            if v.version_number == version:
                                matching_version = v
                                break
                        if matching_version:
                            # Create a note with only that version
                            note.current_version = version
                            note.versions = [matching_version]
                        else:
                            return None  # Version not found
                    
                    return note
        return None
    
    def get_notes_by_type(self, note_type: NoteType, limit: int = 50) -> List[Note]:
        """Get notes filtered by type."""
        result = []
        count = 0
        
        with open(self.notes_file, "r") as f:
            for line in f:
                if count >= limit:
                    break
                if not line.strip():
                    continue
                note_data = json.loads(line)
                if NoteType(note_data['type']) == note_type:
                    note = Note(
                        note_id=note_data['note_id'],
                        title=note_data['title'],
                        type=NoteType(note_data['type']),
                        ticker=note_data.get('ticker'),
                        sector=note_data.get('sector'),
                        created_at=note_data['created_at'],
                        updated_at=note_data['updated_at'],
                        current_version=note_data['current_version'],
                        versions=[NoteVersion(**v) for v in note_data['versions']],
                        status=note_data['status'],
                        related_notes=note_data['related_notes'],
                        metadata=note_data.get('metadata', {})
                    )
                    result.append(note)
                    count += 1
        
        return result
    
    def get_notes_by_ticker(self, ticker: str, limit: int = 50) -> List[Note]:
        """Get notes related to a specific ticker."""
        result = []
        count = 0
        
        with open(self.notes_file, "r") as f:
            for line in f:
                if count >= limit:
                    break
                if not line.strip():
                    continue
                note_data = json.loads(line)
                if note_data.get('ticker', '').upper() == ticker.upper():
                    note = Note(
                        note_id=note_data['note_id'],
                        title=note_data['title'],
                        type=NoteType(note_data['type']),
                        ticker=note_data.get('ticker'),
                        sector=note_data.get('sector'),
                        created_at=note_data['created_at'],
                        updated_at=note_data['updated_at'],
                        current_version=note_data['current_version'],
                        versions=[NoteVersion(**v) for v in note_data['versions']],
                        status=note_data['status'],
                        related_notes=note_data['related_notes'],
                        metadata=note_data.get('metadata', {})
                    )
                    result.append(note)
                    count += 1
        
        return result
    
    def get_all_notes(self, limit: int = 100) -> List[Note]:
        """Get all notes up to the limit."""
        result = []
        count = 0
        
        with open(self.notes_file, "r") as f:
            for line in f:
                if count >= limit:
                    break
                if not line.strip():
                    continue
                note_data = json.loads(line)
                note = Note(
                    note_id=note_data['note_id'],
                    title=note_data['title'],
                    type=NoteType(note_data['type']),
                    ticker=note_data.get('ticker'),
                    sector=note_data.get('sector'),
                    created_at=note_data['created_at'],
                    updated_at=note_data['updated_at'],
                    current_version=note_data['current_version'],
                    versions=[NoteVersion(**v) for v in note_data['versions']],
                    status=note_data['status'],
                    related_notes=note_data['related_notes'],
                    metadata=note_data.get('metadata', {})
                )
                result.append(note)
                count += 1
        
        return result
    
    def search_notes(self, query: str, ticker: Optional[str] = None, 
                    note_type: Optional[NoteType] = None, 
                    tags: Optional[List[str]] = None, limit: int = 50) -> List[Note]:
        """Search notes by content, ticker, type, or tags."""
        result = []
        count = 0
        
        query_lower = query.lower() if query else ""
        
        with open(self.notes_file, "r") as f:
            for line in f:
                if count >= limit:
                    break
                if not line.strip():
                    continue
                note_data = json.loads(line)
                
                # Apply filters
                if ticker and note_data.get('ticker', '').upper() != ticker.upper():
                    continue
                if note_type and NoteType(note_data['type']) != note_type:
                    continue
                if tags:
                    note_tags = note_data['versions'][0]['tags'] if note_data['versions'] else []
                    if not any(tag in note_tags for tag in tags):
                        continue
                
                # Search in title, content, and summary
                matches = False
                if query_lower:
                    # Check title
                    if query_lower in note_data['title'].lower():
                        matches = True
                    # Check content in versions
                    for version in note_data['versions']:
                        if query_lower in version['content'].lower() or query_lower in version.get('summary', '').lower():
                            matches = True
                            break
                else:
                    matches = True  # If no query, return all matching filters
                
                if matches:
                    note = Note(
                        note_id=note_data['note_id'],
                        title=note_data['title'],
                        type=NoteType(note_data['type']),
                        ticker=note_data.get('ticker'),
                        sector=note_data.get('sector'),
                        created_at=note_data['created_at'],
                        updated_at=note_data['updated_at'],
                        current_version=note_data['current_version'],
                        versions=[NoteVersion(**v) for v in note_data['versions']],
                        status=note_data['status'],
                        related_notes=note_data['related_notes'],
                        metadata=note_data.get('metadata', {})
                    )
                    result.append(note)
                    count += 1
        
        return result
    
    def get_version_history(self, note_id: str) -> List[NoteVersion]:
        """Get the version history of a specific note."""
        note = self.get_note(note_id)
        if note:
            return note.versions
        return []
    
    def compare_versions(self, note_id: str, v1: int, v2: int) -> Dict[str, Any]:
        """Compare two versions of a note."""
        note = self.get_note(note_id)
        if not note:
            return {}
        
        version1 = None
        version2 = None
        
        for v in note.versions:
            if v.version_number == v1:
                version1 = v
            if v.version_number == v2:
                version2 = v
        
        if not version1 or not version2:
            return {}
        
        return {
            "note_id": note_id,
            "comparison": {
                "version1": {
                    "version_number": version1.version_number,
                    "timestamp": version1.timestamp,
                    "author": version1.author,
                    "summary": version1.summary
                },
                "version2": {
                    "version_number": version2.version_number,
                    "timestamp": version2.timestamp,
                    "author": version2.author,
                    "summary": version2.summary
                },
                "content_diff": {
                    "length_v1": len(version1.content),
                    "length_v2": len(version2.content),
                    "pct_change": abs(len(version1.content) - len(version2.content)) / max(len(version1.content), 1) * 100
                }
            }
        }
