#!/usr/bin/env python3
"""
Temporal Bash History Analyzer - Identifies commands used across multiple non-adjacent days
to distinguish recurring workflows from temporary intensive tasks
"""

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import os


class TemporalAnalyzer:
    def __init__(self):
        self.commands = []
        self.all_commands = Counter()  # Unified tracking for all command patterns
        self.command_dates = defaultdict(set)  # command -> set of dates
        self.valid_commands = set()
        self.invalid_commands = set()
        self.skipped_count = 0
        self.skip_reasons = Counter()
        
    def parse_timestamp(self, line):
        """Extract timestamp from bash history line"""
        # Look for timestamp format: #1234567890
        timestamp_match = re.match(r'^#(\d+)', line.strip())
        if timestamp_match:
            timestamp = int(timestamp_match.group(1))
            return datetime.fromtimestamp(timestamp).date()
        return None
    

        
    def is_valid_command(self, cmd_word):
        """Check if a command word is a valid executable using 'type' command"""
        if cmd_word in self.valid_commands:
            return True
        if cmd_word in self.invalid_commands:
            return False
            
        try:
            result = subprocess.run(['type', cmd_word], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True, 
                                  shell=True)
            
            if result.returncode == 0:
                self.valid_commands.add(cmd_word)
                return True
            else:
                self.invalid_commands.add(cmd_word)
                return False
                
        except subprocess.SubprocessError:
            self.invalid_commands.add(cmd_word)
            return False
    
    def read_history(self):
        """Read bash history with timestamps"""
        history_entries = []
        history_file = Path.home() / ".bash_history"
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                current_date = None
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this is a timestamp line
                    date = self.parse_timestamp(line)
                    if date:
                        current_date = date
                        continue
                    
                    # This is a command line
                    history_entries.append((line, current_date))
                
                print(f"Read {len(history_entries)} entries from {history_file}")
            except Exception as e:
                print(f"Error reading {history_file}: {e}")
        
        return history_entries
    
    def clean_command(self, command):
        """Clean and normalize a command"""
        command = command.strip()
        
        if not command or command.startswith('#'):
            return None
        
        # Normalize whitespace around common operators to group similar commands
        # This makes "git fetch&&git" and "git fetch && git" equivalent
        operators = ['&&', '||', '|', ';', '>', '>>', '<', '<<']
        
        for op in operators:
            # Replace variations like "cmd&&cmd", "cmd &&cmd", "cmd&& cmd", "cmd && cmd"
            # with standardized "cmd && cmd" (spaces around operators)
            pattern = rf'\s*{re.escape(op)}\s*'
            command = re.sub(pattern, f' {op} ', command)
        
        # Clean up any double spaces that might result
        command = re.sub(r'\s+', ' ', command).strip()
        
        return command
    
    def count_non_adjacent_days(self, dates):
        """Count non-adjacent days in a set of dates"""
        if not dates:
            return 0
            
        sorted_dates = sorted(dates)
        non_adjacent_count = 1  # First date is always non-adjacent
        
        for i in range(1, len(sorted_dates)):
            # If there's more than 1 day gap, it's non-adjacent
            if (sorted_dates[i] - sorted_dates[i-1]).days > 1:
                non_adjacent_count += 1
        
        return non_adjacent_count
    
    def analyze_commands(self, command_entries, min_non_adjacent_days=5):
        """Analyze commands with temporal filtering"""
        print("Analyzing commands with temporal filtering...")
        
        for i, (cmd, date) in enumerate(command_entries):
            if i % 1000 == 0:
                print(f"Processed {i}/{len(command_entries)} commands...")
                
            cleaned = self.clean_command(cmd)
            if not cleaned:
                continue
                
            parts = cleaned.split()
            if not parts:
                continue
            
            first_word = parts[0]
            
            if first_word in ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'case', 'esac']:
                self.skipped_count += 1
                self.skip_reasons['shell_construct'] += 1
                continue
                
            if not self.is_valid_command(first_word):
                self.skipped_count += 1
                self.skip_reasons['invalid_command'] += 1
                continue
                
            if len(first_word) > 50:
                self.skipped_count += 1
                self.skip_reasons['too_long'] += 1
                continue
                
            # Track all patterns: full command, first word, and multi-word patterns
            patterns_to_track = [cleaned, first_word]  # Full command and root command
            
            # Add multi-word patterns (2-word, 3-word, etc.)
            for length in range(2, min(6, len(parts) + 1)):
                pattern = ' '.join(parts[:length])
                patterns_to_track.append(pattern)
            
            # Track dates and counts for all patterns
            for pattern in patterns_to_track:
                if date:
                    self.command_dates[pattern].add(date)
                self.all_commands[pattern] += 1
            
            # Keep original commands list for reference
            self.commands.append(cleaned)
        
        print(f"Initial filtering complete. Skipped {self.skipped_count} invalid commands.")
        
        # Now filter by temporal criteria
        print(f"Applying temporal filter: minimum {min_non_adjacent_days} non-adjacent days...")
        self.filter_by_temporal_usage(min_non_adjacent_days)
    
    def filter_by_temporal_usage(self, min_non_adjacent_days):
        """Filter commands by non-adjacent day usage"""
        # Filter all commands uniformly
        temporal_commands = Counter()
        for cmd, count in self.all_commands.items():
            non_adjacent_days = self.count_non_adjacent_days(self.command_dates[cmd])
            if non_adjacent_days >= min_non_adjacent_days:
                temporal_commands[cmd] = count
        
        # Calculate filtering statistics
        original_count = len(self.all_commands)
        filtered_count = original_count - len(temporal_commands)
        
        # Update to filtered commands
        self.all_commands = temporal_commands
        
        print(f"Temporal filtering removed {filtered_count} command patterns")
        print(f"(kept only commands used on {min_non_adjacent_days}+ non-adjacent days)")
    
    def analyze_root_commands(self):
        """Analyze commands by root to decide optimal aliasing strategy"""
        # Group commands by their root (first word)
        root_groups = defaultdict(list)
        
        for cmd, count in self.all_commands.items():
            if ' ' in cmd:  # Multi-word command
                root = cmd.split()[0]
                root_groups[root].append({
                    'command': cmd,
                    'count': count,
                    'savings_potential': (len(cmd) - 2) * count  # Assume 2-char alias
                })
        
        # Analyze each root group
        alias_recommendations = []
        
        for root, commands in root_groups.items():
            if not commands:
                continue
                
            # Calculate total usage of root vs individual patterns
            total_pattern_usage = sum(cmd['count'] for cmd in commands)
            root_usage = self.all_commands.get(root, 0)
            
            # Calculate potential savings for each approach
            # Option 1: Alias the root command
            if root_usage > 0:
                root_alias_savings = (len(root) - 1) * (root_usage + total_pattern_usage)
            else:
                root_alias_savings = 0
            
            # Option 2: Alias individual patterns
            pattern_alias_savings = sum(cmd['savings_potential'] for cmd in commands)
            
            # Decision logic
            if root_alias_savings > pattern_alias_savings * 1.2:  # 20% bonus for simplicity
                # Recommend aliasing the root
                if root_usage + total_pattern_usage >= 5:  # Minimum usage threshold
                    alias_recommendations.append({
                        'type': 'root',
                        'original': root,
                        'alias': root[0],  # Single letter alias
                        'count': root_usage + total_pattern_usage,
                        'savings': root_alias_savings,
                        'patterns': [cmd['command'] for cmd in commands]
                    })
            else:
                # Recommend individual pattern aliases
                for cmd in commands:
                    if cmd['count'] >= 3:  # Minimum usage threshold
                        alias_recommendations.append({
                            'type': 'pattern',
                            'original': cmd['command'],
                            'alias': self.generate_alias(cmd['command']),
                            'count': cmd['count'],
                            'savings': cmd['savings_potential'],
                            'patterns': [cmd['command']]
                        })
        
        return alias_recommendations
    
    def analyze_bash_functions(self):
        """Analyze commands for common prefixes that could be bash functions"""
        # Group commands by their prefixes (first 3-4 words)
        prefix_groups = defaultdict(list)
        
        for cmd, count in self.all_commands.items():
            if ' ' in cmd:  # Multi-word command
                parts = cmd.split()
                if len(parts) >= 3:  # At least 3 words for a meaningful prefix
                    # Try different prefix lengths
                    for prefix_len in [3, 4, 5]:
                        if len(parts) >= prefix_len:
                            prefix = ' '.join(parts[:prefix_len])
                            prefix_groups[prefix].append({
                                'command': cmd,
                                'count': count,
                                'remaining': ' '.join(parts[prefix_len:]) if len(parts) > prefix_len else ''
                            })
        
        # Analyze prefix groups for function opportunities
        function_recommendations = []
        
        for prefix, commands in prefix_groups.items():
            if len(commands) < 2:  # Need at least 2 different variations
                continue
                
            # Calculate total usage and variety
            total_usage = sum(cmd['count'] for cmd in commands)
            unique_suffixes = len(set(cmd['remaining'] for cmd in commands if cmd['remaining']))
            
            # Only suggest if there's real variety in the suffixes
            if total_usage >= 10 and unique_suffixes >= 2:
                # Generate function name
                func_name = self.generate_function_name(prefix)
                
                # Calculate potential savings
                avg_prefix_len = len(prefix)
                func_call_len = len(f"{func_name} ")
                chars_saved_per_use = avg_prefix_len - func_call_len
                
                if chars_saved_per_use > 0:
                    total_chars_saved = chars_saved_per_use * total_usage
                    
                    # Get temporal info
                    all_dates = set()
                    for cmd_info in commands:
                        all_dates.update(self.command_dates.get(cmd_info['command'], set()))
                    
                    non_adjacent_days = self.count_non_adjacent_days(all_dates)
                    date_span = max(all_dates) - min(all_dates) if all_dates else timedelta(0)
                    
                    function_recommendations.append({
                        'prefix': prefix,
                        'func_name': func_name,
                        'total_usage': total_usage,
                        'variations': len(commands),
                        'unique_suffixes': unique_suffixes,
                        'commands': [cmd['command'] for cmd in commands[:3]],  # Top 3 examples
                        'chars_per_use': chars_saved_per_use,
                        'total_chars_saved': total_chars_saved,
                        'non_adjacent_days': non_adjacent_days,
                        'date_span': date_span.days if all_dates else 0
                    })
        
        # Sort by total savings potential
        function_recommendations.sort(key=lambda x: x['total_chars_saved'], reverse=True)
        
        return function_recommendations
    
    def generate_function_name(self, prefix):
        """Generate a meaningful function name from a command prefix"""
        parts = prefix.split()
        
        # Create function name from first letters or meaningful abbreviations
        if len(parts) >= 3:
            # For patterns like "g fetch && g log" -> "gfl"
            if parts[0] == 'g' and '&&' in parts:
                # Take first letter of each command part
                name_parts = []
                for part in parts:
                    if part != '&&':
                        name_parts.append(part[0])
                func_name = ''.join(name_parts)
            else:
                # Generic: take first letter of each meaningful word
                meaningful_words = [p for p in parts if len(p) > 1 and p not in ['&&', '||', '|']]
                func_name = ''.join(p[0] for p in meaningful_words[:3])
        else:
            func_name = ''.join(p[0] for p in parts)
        
        return func_name.lower()
    
    def analyze_environment_variables(self):
        """Analyze commands for frequently used strings that could be environment variables"""
        # Extract any repeated string patterns from all commands
        string_usage = defaultdict(list)  # string -> list of (command, count) tuples
        
        for cmd, count in self.all_commands.items():
            # Look for various repeatable string patterns
            patterns_to_check = [
                # Git branch/remote patterns
                r'origin/[\w/.-]+',
                r'upstream/[\w/.-]+',
                # Paths (absolute and relative)
                r'/[\w/.-]{6,}',
                r'[\w.-]+/[\w/.-]{6,}',
                # URLs and network patterns
                r'https?://[\w/.-]+',
                r'[\w.-]+\.[\w.-]+/[\w/.-]+',
                r'[\w.-]+:\d+',  # host:port
                # File extensions and patterns
                r'--[\w-]+=[\w/.-]{4,}',  # --flag=value
                r'--[\w-]{4,}',  # --long-flag
                r'-[\w]{2,}',  # multi-char flags like -la, -rf
                # Version/hash patterns
                r'v\d+\.\d+[\w.-]*',  # version numbers
                r'[a-f0-9]{8,}',  # hex strings (commit hashes, etc.)
                # File patterns
                r'[\w.-]+\.[\w]{2,4}',  # file.extension
                # Command sequences
                r'[\w.-]{4,}',  # any word-like string 4+ chars
            ]
            
            for pattern in patterns_to_check:
                matches = re.findall(pattern, cmd)
                for match in matches:
                    # Filter criteria for environment variable candidates
                    if (len(match) >= 4 and  # Minimum length
                        not match.isdigit() and  # Not just a number
                        not re.match(r'^-[a-zA-Z]$', match) and  # Not single letter flags
                        not match in ['true', 'false', 'null', 'none'] and  # Not common values
                        len(set(match)) > 2):  # Has some variety in characters
                        string_usage[match].append((cmd, count))
        
        # Analyze string usage frequency
        env_var_candidates = []
        
        for string_pattern, usages in string_usage.items():
            # Calculate total usage across all commands
            total_usage = sum(count for _, count in usages)
            command_count = len(usages)
            
            # Adjust thresholds based on string type and length
            min_usage = max(5, 20 - len(string_pattern))  # Longer strings need fewer uses
            min_commands = 2 if len(string_pattern) > 10 else 3
            
            # Only suggest if used frequently enough
            if total_usage >= min_usage and command_count >= min_commands:
                # Generate environment variable name
                env_name = self.generate_env_var_name(string_pattern)
                
                # Calculate potential savings
                # Each usage saves (len(string) - len($ENV_NAME))
                var_ref_length = len(f"${env_name}")
                chars_saved_per_use = len(string_pattern) - var_ref_length
                
                if chars_saved_per_use > 0:
                    total_chars_saved = chars_saved_per_use * total_usage
                    
                    # Get temporal info for the string
                    all_dates = set()
                    for cmd, _ in usages:
                        all_dates.update(self.command_dates.get(cmd, set()))
                    
                    non_adjacent_days = self.count_non_adjacent_days(all_dates)
                    date_span = max(all_dates) - min(all_dates) if all_dates else timedelta(0)
                    
                    env_var_candidates.append({
                        'string': string_pattern,
                        'env_name': env_name,
                        'total_usage': total_usage,
                        'command_count': command_count,
                        'commands': [cmd for cmd, _ in usages],
                        'chars_per_use': chars_saved_per_use,
                        'total_chars_saved': total_chars_saved,
                        'non_adjacent_days': non_adjacent_days,
                        'date_span': date_span.days if all_dates else 0,
                        'string_type': self.classify_string_type(string_pattern)
                    })
        
        # Sort by total savings potential
        env_var_candidates.sort(key=lambda x: x['total_chars_saved'], reverse=True)
        
        return env_var_candidates
    
    def classify_string_type(self, string_pattern):
        """Classify the type of string for better categorization"""
        if re.match(r'^https?://', string_pattern):
            return 'URL'
        elif re.match(r'^/', string_pattern):
            return 'Path'
        elif re.match(r'[\w.-]+/[\w/.-]+', string_pattern):
            return 'Path/Branch'
        elif re.match(r'--[\w-]+', string_pattern):
            return 'Flag'
        elif re.match(r'[\w.-]+:\d+', string_pattern):
            return 'Host:Port'
        elif re.match(r'[a-f0-9]{8,}', string_pattern):
            return 'Hash'
        elif re.match(r'v\d+\.\d+', string_pattern):
            return 'Version'
        elif re.match(r'[\w.-]+\.[\w]{2,4}$', string_pattern):
            return 'File'
        else:
            return 'String'
    
    def generate_env_var_name(self, string_pattern):
        """Generate a meaningful environment variable name for any string pattern"""
        clean_string = string_pattern
        
        # Handle different string types
        if re.match(r'^https?://', string_pattern):
            # URL handling
            clean_string = re.sub(r'^https?://', '', clean_string)
            clean_string = re.sub(r'/.*$', '', clean_string)  # Keep just hostname
            prefix = "URL"
        elif re.match(r'^--[\w-]+', string_pattern):
            # Flag handling
            clean_string = re.sub(r'^--', '', string_pattern)
            prefix = "FLAG"
        elif re.match(r'^origin/', string_pattern):
            # Git branch/remote
            clean_string = re.sub(r'^origin/', '', string_pattern)
            prefix = "BRANCH"
        elif re.match(r'^/', string_pattern):
            # Absolute path
            clean_string = re.sub(r'^/proj_risc/user_dev/[\w]+/', '', clean_string)
            clean_string = re.sub(r'^/home/[\w]+/', '', clean_string)
            clean_string = re.sub(r'^/', '', clean_string)
            prefix = ""
        elif re.match(r'[\w.-]+:\d+', string_pattern):
            # Host:port
            clean_string = re.sub(r':\d+$', '', string_pattern)
            prefix = "HOST"
        elif re.match(r'[a-f0-9]{8,}', string_pattern):
            # Hash/commit
            return "COMMIT_HASH"
        elif re.match(r'v\d+\.\d+', string_pattern):
            # Version
            return "VERSION"
        else:
            prefix = ""
        
        # Split into meaningful parts
        parts = re.split(r'[/._-]', clean_string)
        
        # Filter meaningful parts (not empty, not single chars, not numbers only)
        meaningful_parts = [p for p in parts if len(p) > 1 and not p.isdigit()]
        
        if not meaningful_parts:
            # Fallback - use original string parts
            parts = string_pattern.split('/')
            meaningful_parts = [p for p in parts if len(p) > 1][-2:]
        
        # Create env var name from parts
        if len(meaningful_parts) >= 2:
            base_name = '_'.join(meaningful_parts[:2])
        elif meaningful_parts:
            base_name = meaningful_parts[0]
        else:
            base_name = "VAR"
        
        # Combine prefix and base name
        if prefix:
            env_name = f"{prefix}_{base_name}".upper()
        else:
            env_name = base_name.upper()
        
        # Clean up the name
        env_name = re.sub(r'[^A-Z0-9_]', '_', env_name)
        env_name = re.sub(r'_+', '_', env_name)
        env_name = env_name.strip('_')
        
        # Ensure it's not too long
        if len(env_name) > 20:
            env_name = env_name[:20]
        
        return env_name
    
    def generate_alias(self, command):
        """Generate a short alias for a command"""
        parts = command.split()
        
        if len(parts) == 2:
            return parts[0][0] + parts[1][0]
        elif parts[0] in ['git', 'g', 'docker', 'npm', 'pip']:
            return parts[0][0] + ''.join(p[0] for p in parts[1:3])
        else:
            return ''.join(p[0] for p in parts[:3])
    
    def calculate_temporal_savings(self):
        """Calculate savings for temporally recurring commands using smart alias logic"""
        print("=" * 80)
        print("TEMPORAL SAVINGS ANALYSIS (Smart Aliasing & Environment Variables)")
        print("=" * 80)
        
        # Get smart alias recommendations
        alias_recommendations = self.analyze_root_commands()
        
        # Get bash function recommendations
        function_recommendations = self.analyze_bash_functions()
        
        # Get environment variable recommendations
        env_var_recommendations = self.analyze_environment_variables()
        
        # Sort by savings potential
        alias_recommendations.sort(key=lambda x: x['savings'], reverse=True)
        
        total_chars_saved = 0
        total_commands_affected = 0
        savings_data = []
        
        for rec in alias_recommendations[:25]:  # Top 25 recommendations
            cmd = rec['original']
            alias_name = rec['alias']
            count = rec['count']
            
            # Calculate actual savings
            original_length = len(cmd)
            alias_length = len(alias_name)
            chars_saved_per_use = original_length - alias_length
            total_chars_saved_cmd = chars_saved_per_use * count
            
            # Get temporal info
            dates = self.command_dates[cmd]
            non_adjacent_days = self.count_non_adjacent_days(dates)
            date_span = max(dates) - min(dates) if dates else timedelta(0)
            
            if chars_saved_per_use > 0:
                total_chars_saved += total_chars_saved_cmd
                total_commands_affected += count
                
                savings_data.append({
                    'original': cmd,
                    'alias': alias_name,
                    'count': count,
                    'chars_per_use': chars_saved_per_use,
                    'total_chars': total_chars_saved_cmd,
                    'non_adjacent_days': non_adjacent_days,
                    'date_span': date_span.days,
                    'type': rec['type']
                })
        
        # Sort by total character savings
        savings_data.sort(key=lambda x: x['total_chars'], reverse=True)
        
        print(f"SMART ALIAS SUGGESTIONS (Root vs Pattern Analysis):")
        print("-" * 95)
        print(f"{'Rank':<4} {'Original Command':<30} {'Alias':<8} {'Type':<8} {'Uses':<6} {'Days':<6} {'Span':<8} {'Savings':<15}")
        print("-" * 95)
        
        for i, data in enumerate(savings_data[:20], 1):
            alias_type = data.get('type', 'pattern')[:7]  # Truncate to fit
            print(f"{i:3d}. {data['original']:<30} {data['alias']:<8} "
                  f"{alias_type:<8} {data['count']:4d}x  {data['non_adjacent_days']:4d}d  {data['date_span']:6d}d  "
                  f"{data['chars_per_use']:2d}×{data['count']} = {data['total_chars']:4d} chars")
        
        # Display bash function suggestions
        print(f"\nBASH FUNCTION SUGGESTIONS (Common Prefixes):")
        print("-" * 105)
        print(f"{'Rank':<4} {'Common Prefix':<35} {'Function':<8} {'Uses':<6} {'Vars':<5} {'Days':<6} {'Savings':<15}")
        print("-" * 105)
        
        func_total_chars_saved = 0
        func_total_usage = 0
        
        for i, func_data in enumerate(function_recommendations[:10], 1):
            func_total_chars_saved += func_data['total_chars_saved']
            func_total_usage += func_data['total_usage']
            
            print(f"{i:3d}. {func_data['prefix']:<35} {func_data['func_name']:<8} "
                  f"{func_data['total_usage']:4d}x  {func_data['variations']:3d}   {func_data['non_adjacent_days']:4d}d  "
                  f"{func_data['chars_per_use']:2d}×{func_data['total_usage']} = {func_data['total_chars_saved']:4d} chars")
        
        if function_recommendations:
            print(f"\nExample function for top suggestion:")
            top_func = function_recommendations[0]
            print(f"  {top_func['func_name']}() {{")
            print(f"      {top_func['prefix']} \"$@\"")
            print(f"  }}")
            if top_func['commands']:
                example_cmd = top_func['commands'][0]
                remaining = example_cmd[len(top_func['prefix']):].strip()
                print(f"  Usage: {top_func['func_name']} {remaining}")
        
        # Display environment variable suggestions
        print(f"\nENVIRONMENT VARIABLE SUGGESTIONS (Frequent Strings):")
        print("-" * 105)
        print(f"{'Rank':<4} {'String':<35} {'Type':<8} {'Env Var':<15} {'Uses':<6} {'Cmds':<5} {'Days':<6} {'Savings':<15}")
        print("-" * 105)
        
        env_total_chars_saved = 0
        env_total_usage = 0
        
        for i, env_data in enumerate(env_var_recommendations[:15], 1):
            env_total_chars_saved += env_data['total_chars_saved']
            env_total_usage += env_data['total_usage']
            
            string_type = env_data.get('string_type', 'String')[:7]  # Truncate to fit
            print(f"{i:3d}. {env_data['string']:<35} {string_type:<8} ${env_data['env_name']:<14} "
                  f"{env_data['total_usage']:4d}x  {env_data['command_count']:3d}   {env_data['non_adjacent_days']:4d}d  "
                  f"{env_data['chars_per_use']:2d}×{env_data['total_usage']} = {env_data['total_chars_saved']:4d} chars")
        
        if env_var_recommendations:
            print(f"\nExample usage for top suggestion:")
            top_env = env_var_recommendations[0]
            print(f"  export {top_env['env_name']}=\"{top_env['string']}\"")
            if top_env['commands']:
                example_cmd = top_env['commands'][0]
                replaced_cmd = example_cmd.replace(top_env['string'], f"${top_env['env_name']}")
                print(f"  Before: {example_cmd}")
                print(f"  After:  {replaced_cmd}")
        
        # Update total savings to include functions and environment variables
        total_chars_saved += func_total_chars_saved + env_total_chars_saved
        total_commands_affected += func_total_usage + env_total_usage
        
        print(f"\nCOMBINED SAVINGS SUMMARY:")
        print(f"- Alias savings: {total_chars_saved - func_total_chars_saved - env_total_chars_saved:,} chars")
        print(f"- Function savings: {func_total_chars_saved:,} chars")
        print(f"- Environment variable savings: {env_total_chars_saved:,} chars")
        print(f"- TOTAL characters saved: {total_chars_saved:,} chars")
        print(f"- Commands/usages affected: {total_commands_affected:,}")
        print(f"- Recurring commands analyzed: {len(self.commands):,}")
        print(f"- One-off commands filtered: {self.skipped_count:,}")
        
        if total_commands_affected > 0:
            print(f"- Average savings per usage: {total_chars_saved/total_commands_affected:.1f} characters")
            time_saved_minutes = total_chars_saved / 200
            print(f"- Estimated time saved: {time_saved_minutes:.1f} minutes")
        
        # Generate output files
        self.generate_output_files(alias_recommendations, function_recommendations, env_var_recommendations)
        print()
        
        return savings_data
    
    def generate_output_files(self, alias_recommendations, function_recommendations, env_var_recommendations):
        """Generate properly formatted alias, function, and export files"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate aliases file
        aliases_file = "/tmp/bash_aliases_suggestions.sh"
        with open(aliases_file, 'w') as f:
            f.write(f"#!/bin/bash\n")
            f.write(f"# Bash Aliases - Generated by Temporal Analyzer on {timestamp}\n")
            f.write(f"# Based on analysis of commands used across 5+ non-adjacent days\n")
            f.write(f"# Source this file or add to your ~/.bashrc or ~/.bash_aliases\n\n")
            
            # Sort alias recommendations by savings
            sorted_aliases = sorted(alias_recommendations, key=lambda x: x['savings'], reverse=True)
            
            used_aliases = set()  # Track used alias names to avoid duplicates
            
            for i, rec in enumerate(sorted_aliases[:20], 1):  # Top 20
                original = rec['original']
                alias_name = rec['alias']
                count = rec['count']
                savings = rec['savings']
                
                # Ensure unique alias names
                base_alias = alias_name
                counter = 1
                while alias_name in used_aliases:
                    alias_name = f"{base_alias}{counter}"
                    counter += 1
                used_aliases.add(alias_name)
                
                # Clean up alias name and original command for bash
                clean_original = original.replace("'", "\\'")
                
                f.write(f"# {i:2d}. {original} -> {alias_name} ({count} uses, {savings} chars saved)\n")
                f.write(f"alias {alias_name}='{clean_original}'\n\n")
        
        # Generate functions file
        functions_file = "/tmp/bash_functions_suggestions.sh"
        with open(functions_file, 'w') as f:
            f.write(f"#!/bin/bash\n")
            f.write(f"# Bash Functions - Generated by Temporal Analyzer on {timestamp}\n")
            f.write(f"# Based on analysis of common command prefixes across 5+ non-adjacent days\n")
            f.write(f"# Source this file or add to your ~/.bashrc\n\n")
            
            for i, func_data in enumerate(function_recommendations[:10], 1):  # Top 10
                prefix = func_data['prefix']
                func_name = func_data['func_name']
                usage = func_data['total_usage']
                variations = func_data['variations']
                savings = func_data['total_chars_saved']
                
                f.write(f"# {i:2d}. {prefix} -> {func_name}() ({usage} uses, {variations} variations, {savings} chars saved)\n")
                f.write(f"{func_name}() {{\n")
                f.write(f"    {prefix} \"$@\"\n")
                f.write(f"}}\n\n")
                
                # Add usage examples for top few
                if i <= 3 and func_data['commands']:
                    f.write(f"# Example usage:\n")
                    for j, example_cmd in enumerate(func_data['commands'][:2], 1):
                        remaining = example_cmd[len(prefix):].strip()
                        f.write(f"#   {func_name} {remaining}\n")
                    f.write(f"\n")
        
        # Generate exports file  
        exports_file = "/tmp/bash_exports_suggestions.sh"
        with open(exports_file, 'w') as f:
            f.write(f"#!/bin/bash\n")
            f.write(f"# Environment Variables - Generated by Temporal Analyzer on {timestamp}\n")
            f.write(f"# Based on analysis of strings used across 5+ non-adjacent days\n")
            f.write(f"# Source this file or add to your ~/.bashrc\n\n")
            
            used_env_vars = set()  # Track used env var names to avoid duplicates
            
            for i, env_data in enumerate(env_var_recommendations[:10], 1):  # Top 10
                string_pattern = env_data['string']
                env_name = env_data['env_name']
                usage = env_data['total_usage']
                savings = env_data['total_chars_saved']
                string_type = env_data.get('string_type', 'String')
                
                # Ensure unique environment variable names
                base_env = env_name
                counter = 1
                while env_name in used_env_vars:
                    env_name = f"{base_env}_{counter}"
                    counter += 1
                used_env_vars.add(env_name)
                
                # Clean up the string for bash export
                clean_string = string_pattern.replace("'", "\\'")
                
                f.write(f"# {i:2d}. {string_type}: {string_pattern} -> ${env_name} ({usage} uses, {savings} chars saved)\n")
                f.write(f"export {env_name}='{clean_string}'\n\n")
                
                # Add usage examples for top few
                if i <= 3 and env_data['commands']:
                    f.write(f"# Example usage:\n")
                    example_cmd = env_data['commands'][0]
                    replaced_cmd = example_cmd.replace(string_pattern, f"${env_name}")
                    f.write(f"#   Before: {example_cmd}\n")
                    f.write(f"#   After:  {replaced_cmd}\n\n")
        
        # Print file locations
        print(f"\n📁 OUTPUT FILES GENERATED:")
        print(f"   Aliases:   {aliases_file}")
        print(f"   Functions: {functions_file}")
        print(f"   Exports:   {exports_file}")
        print(f"\n🚀 TO APPLY:")
        print(f"   source {aliases_file}")
        print(f"   source {functions_file}")
        print(f"   source {exports_file}")
        print(f"\n💾 TO MAKE PERMANENT:")
        print(f"   cat {aliases_file} >> ~/.bash_aliases")
        print(f"   cat {functions_file} >> ~/.bashrc")  
        print(f"   cat {exports_file} >> ~/.bashrc")
        
        # Check for HISTCONTROL settings that affect statistics accuracy
        self.check_history_settings()
    
    def check_history_settings(self):
        """Check bash history settings that could affect statistics accuracy"""
        try:
            # Check HISTCONTROL environment variable
            result = subprocess.run(['bash', '-c', 'echo "$HISTCONTROL"'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   universal_newlines=True, timeout=5)
            
            histcontrol = result.stdout.strip()
            
            if histcontrol and ('ignoredups' in histcontrol or 'ignoreboth' in histcontrol):
                print(f"\n⚠️  BASH HISTORY WARNING:")
                print(f"   Your HISTCONTROL is set to '{histcontrol}'")
                print(f"   This ignores consecutive duplicate commands, so:")
                print(f"   📊 Frequency statistics are UNDERESTIMATED")
                print(f"   🔢 Actual usage counts are likely much HIGHER")
                print(f"   💰 Potential savings could be much GREATER")
                print(f"\n   To get accurate statistics, consider temporarily setting:")
                print(f"   export HISTCONTROL=''")
                print(f"   Then rebuild your bash history for a few days.")
            
            # Check HISTSIZE and HISTFILESIZE
            result_size = subprocess.run(['bash', '-c', 'echo "$HISTSIZE:$HISTFILESIZE"'], 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                        universal_newlines=True, timeout=5)
            
            hist_sizes = result_size.stdout.strip().split(':')
            if len(hist_sizes) == 2:
                histsize = hist_sizes[0] if hist_sizes[0] else "unset"
                histfilesize = hist_sizes[1] if hist_sizes[1] else "unset"
                
                # Warn if history is limited
                if histsize.isdigit() and int(histsize) < 10000:
                    print(f"\n💡 HISTORY SIZE NOTICE:")
                    print(f"   Your HISTSIZE is {histsize} (relatively small)")
                    print(f"   Consider increasing it for better analysis:")
                    print(f"   export HISTSIZE=50000")
                    print(f"   export HISTFILESIZE=50000")
                        
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            # Silently ignore if we can't check - don't want to break the analysis
            pass
    
    def show_temporal_summary(self):
        """Show temporal filtering summary"""
        print("TEMPORAL FILTERING SUMMARY:")
        print("-" * 45)
        
        total_processed = len(self.commands) + self.skipped_count
        print(f"Total entries processed: {total_processed:,}")
        print(f"Commands with sufficient temporal recurrence: {len(self.commands):,}")
        print(f"One-off/temporary patterns filtered: {self.skipped_count:,}")
        print()
        
        print("Filtering breakdown:")
        for reason, count in self.skip_reasons.most_common():
            print(f"  - {reason.replace('_', ' ').title()}: {count:,}")
        print()
        
        # Show date range of analysis
        all_dates = set()
        for dates in self.command_dates.values():
            all_dates.update(dates)
        
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            span = (max_date - min_date).days
            print(f"Analysis period: {min_date} to {max_date} ({span} days)")
        print()
    
    def show_top_recurring_commands(self):
        """Show top recurring single-word commands with temporal info"""
        print("TOP 15 RECURRING COMMANDS (Multi-Day Usage):")
        print("-" * 60)
        print(f"{'Rank':<4} {'Command':<20} {'Uses':<6} {'Days':<6} {'Span':<8}")
        print("-" * 60)
        
        # Filter to single-word commands only for this display
        single_word_commands = {cmd: count for cmd, count in self.all_commands.items() 
                               if ' ' not in cmd}
        
        total_commands = len(self.commands)
        for i, (cmd, count) in enumerate(Counter(single_word_commands).most_common(15), 1):
            dates = self.command_dates[cmd]
            non_adjacent_days = self.count_non_adjacent_days(dates)
            date_span = (max(dates) - min(dates)).days if dates else 0
            percentage = (count / total_commands) * 100
            
            print(f"{i:2d}. {cmd:<20} {count:4d}x  {non_adjacent_days:4d}d  {date_span:6d}d ({percentage:4.1f}%)")
        print()
    
    def generate_executive_summary(self, min_non_adjacent_days):
        """Generate executive summary"""
        total_commands = len(self.commands)
        unique_commands = len(set(self.commands))
        total_processed = total_commands + self.skipped_count
        
        print("=" * 80)
        print("TEMPORAL ANALYSIS EXECUTIVE SUMMARY")
        print("=" * 80)
        print(f"Total entries processed: {total_processed:,}")
        print(f"Recurring commands (used on {min_non_adjacent_days}+ non-adjacent days): {total_commands:,}")
        print(f"Temporary/one-off patterns filtered: {self.skipped_count:,}")
        print(f"Unique recurring commands: {unique_commands:,}")
        print(f"Command repetition rate: {((total_commands - unique_commands) / total_commands * 100):.1f}%")
        print(f"Temporal filter effectiveness: {(self.skipped_count / total_processed * 100):.1f}% noise removed")
        print()
        
        print("TOP OPTIMIZATION OPPORTUNITIES:")
        print("1. Create aliases for frequently used recurring multi-word commands")
        print("2. Focus on commands with consistent multi-day usage patterns")
        print("3. Prioritize git workflow optimizations (if they recur)")
        print("4. Ignore temporary project-specific intensive work")
        print()


def main():
    parser = argparse.ArgumentParser(description='Temporal bash history analysis focusing on recurring patterns')
    parser.add_argument('--min-days', type=int, default=5, 
                       help='Minimum non-adjacent days for inclusion (default: 5)')
    parser.add_argument('--min-count', type=int, default=3,
                       help='Minimum usage count (default: 3)')
    
    args = parser.parse_args()
    
    analyzer = TemporalAnalyzer()
    
    print("Performing temporal bash history analysis...")
    print(f"Filtering for commands used on at least {args.min_days} non-adjacent days")
    
    command_entries = analyzer.read_history()
    
    if not command_entries:
        print("No history entries found.")
        return
    
    analyzer.analyze_commands(command_entries, args.min_days)
    
    # Generate all analyses
    analyzer.generate_executive_summary(args.min_days)
    analyzer.show_temporal_summary()
    analyzer.show_top_recurring_commands()
    analyzer.calculate_temporal_savings()


if __name__ == "__main__":
    main() 