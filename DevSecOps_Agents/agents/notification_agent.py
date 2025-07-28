import asyncio
import json
import smtplib
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

from config.config import get_config
from models.database import PipelineIssue, AgentAction, Notification, SessionLocal
from services.groq_service import GroqService
from agents.base_agent import BaseAgent

class NotificationAgent(BaseAgent):
    """Agent for sending notifications about CI/CD issues"""
    
    def __init__(self):
        super().__init__("NotificationAgent")
        self.config = get_config()
        self.groq_service = GroqService()
        
    async def send_notifications(self) -> List[Dict[str, Any]]:
        """Send notifications for pending issues"""
        logger.info("Starting notification sending...")
        
        try:
            db = SessionLocal()
            
            # Get unresolved issues that need notifications
            issues = db.query(PipelineIssue).filter(
                PipelineIssue.status.in_(["open", "investigating"])
            ).all()
            
            notifications_sent = []
            
            for issue in issues:
                # Check if we already sent a notification for this issue recently
                recent_notification = db.query(Notification).filter(
                    Notification.related_issue_id == issue.id,
                    Notification.sent_at > datetime.utcnow() - timedelta(hours=1)
                ).first()
                
                if recent_notification:
                    logger.debug(f"Recent notification already sent for issue {issue.id}, skipping...")
                    continue
                
                # Send notifications based on severity
                if issue.severity in ["critical", "high"]:
                    notifications = await self._send_urgent_notifications(issue)
                else:
                    notifications = await self._send_standard_notifications(issue)
                
                notifications_sent.extend(notifications)
            
            db.close()
            
            logger.info(f"Notification sending completed. Sent {len(notifications_sent)} notifications.")
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Error in notification sending: {e}")
            return []
    
    async def _send_urgent_notifications(self, issue: PipelineIssue) -> List[Dict[str, Any]]:
        """Send urgent notifications for critical/high severity issues"""
        notifications = []
        
        # Send to all configured channels
        if self.config.notifications.slack_webhook:
            notification = await self._send_slack_notification(issue, urgent=True)
            if notification:
                notifications.append(notification)
        
        if self.config.notifications.teams_webhook:
            notification = await self._send_teams_notification(issue, urgent=True)
            if notification:
                notifications.append(notification)
        
        if self.config.notifications.email_smtp:
            notification = await self._send_email_notification(issue, urgent=True)
            if notification:
                notifications.append(notification)
        
        return notifications
    
    async def _send_standard_notifications(self, issue: PipelineIssue) -> List[Dict[str, Any]]:
        """Send standard notifications for medium/low severity issues"""
        notifications = []
        
        # Send to primary notification channel (Slack if available, otherwise email)
        if self.config.notifications.slack_webhook:
            notification = await self._send_slack_notification(issue, urgent=False)
            if notification:
                notifications.append(notification)
        elif self.config.notifications.email_smtp:
            notification = await self._send_email_notification(issue, urgent=False)
            if notification:
                notifications.append(notification)
        
        return notifications
    
    async def _send_slack_notification(self, issue: PipelineIssue, urgent: bool = False) -> Optional[Dict[str, Any]]:
        """Send notification to Slack"""
        try:
            # Create message content
            message = await self._create_notification_message(issue, "slack")
            
            # Prepare Slack payload
            color = "#ff0000" if urgent else "#ffa500"  # Red for urgent, orange for standard
            emoji = "🚨" if urgent else "⚠️"
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"{emoji} {issue.title}",
                        "text": message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": issue.severity.upper(),
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": issue.status.upper(),
                                "short": True
                            },
                            {
                                "title": "Issue Type",
                                "value": issue.issue_type.replace("_", " ").title(),
                                "short": True
                            },
                            {
                                "title": "Detected",
                                "value": issue.detected_at.strftime("%Y-%m-%d %H:%M UTC"),
                                "short": True
                            }
                        ],
                        "footer": "DevSecOps AI Monitoring",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            # Send to Slack
            response = requests.post(
                self.config.notifications.slack_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Save notification record
                notification = await self._save_notification(
                    "slack",
                    "DevSecOps Team",
                    issue.title,
                    message,
                    issue.id
                )
                
                logger.info(f"Slack notification sent for issue {issue.id}")
                return notification
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return None
    
    async def _send_teams_notification(self, issue: PipelineIssue, urgent: bool = False) -> Optional[Dict[str, Any]]:
        """Send notification to Microsoft Teams"""
        try:
            # Create message content
            message = await self._create_notification_message(issue, "teams")
            
            # Prepare Teams payload
            theme_color = "FF0000" if urgent else "FFA500"  # Red for urgent, orange for standard
            emoji = "🚨" if urgent else "⚠️"
            
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": theme_color,
                "summary": f"{emoji} {issue.title}",
                "sections": [
                    {
                        "activityTitle": f"{emoji} {issue.title}",
                        "activitySubtitle": f"Severity: {issue.severity.upper()} | Status: {issue.status.upper()}",
                        "text": message,
                        "facts": [
                            {
                                "name": "Issue Type",
                                "value": issue.issue_type.replace("_", " ").title()
                            },
                            {
                                "name": "Detected",
                                "value": issue.detected_at.strftime("%Y-%m-%d %H:%M UTC")
                            },
                            {
                                "name": "Severity",
                                "value": issue.severity.upper()
                            }
                        ]
                    }
                ]
            }
            
            # Send to Teams
            response = requests.post(
                self.config.notifications.teams_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Save notification record
                notification = await self._save_notification(
                    "teams",
                    "DevSecOps Team",
                    issue.title,
                    message,
                    issue.id
                )
                
                logger.info(f"Teams notification sent for issue {issue.id}")
                return notification
            else:
                logger.error(f"Failed to send Teams notification: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending Teams notification: {e}")
            return None
    
    async def _send_email_notification(self, issue: PipelineIssue, urgent: bool = False) -> Optional[Dict[str, Any]]:
        """Send notification via email"""
        try:
            # Create message content
            message = await self._create_notification_message(issue, "email")
            
            # Prepare email
            subject = f"[{'URGENT' if urgent else 'ALERT'}] {issue.title}"
            
            # Create HTML email
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: {'#ff0000' if urgent else '#ffa500'}; color: white; padding: 15px; border-radius: 5px; }}
                    .content {{ margin: 20px 0; }}
                    .field {{ margin: 10px 0; }}
                    .field-label {{ font-weight: bold; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>{'🚨 URGENT' if urgent else '⚠️ ALERT'}: {issue.title}</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                    <div class="field">
                        <span class="field-label">Severity:</span> {issue.severity.upper()}
                    </div>
                    <div class="field">
                        <span class="field-label">Status:</span> {issue.status.upper()}
                    </div>
                    <div class="field">
                        <span class="field-label">Issue Type:</span> {issue.issue_type.replace("_", " ").title()}
                    </div>
                    <div class="field">
                        <span class="field-label">Detected:</span> {issue.detected_at.strftime("%Y-%m-%d %H:%M UTC")}
                    </div>
                </div>
                <div class="footer">
                    <p>This is an automated notification from DevSecOps AI Monitoring System.</p>
                </div>
            </body>
            </html>
            """
            
            # Send email
            if self.config.notifications.email_smtp and self.config.notifications.email_user and self.config.notifications.email_password:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.config.notifications.email_user
                msg['To'] = self.config.notifications.email_user  # Send to self for now
                
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
                # Connect to SMTP server
                server = smtplib.SMTP(self.config.notifications.email_smtp, 587)
                server.starttls()
                server.login(self.config.notifications.email_user, self.config.notifications.email_password)
                
                # Send email
                server.send_message(msg)
                server.quit()
                
                # Save notification record
                notification = await self._save_notification(
                    "email",
                    self.config.notifications.email_user,
                    subject,
                    message,
                    issue.id
                )
                
                logger.info(f"Email notification sent for issue {issue.id}")
                return notification
            else:
                logger.warning("Email configuration incomplete, skipping email notification")
                return None
                
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return None
    
    async def _create_notification_message(self, issue: PipelineIssue, channel: str) -> str:
        """Create notification message content"""
        try:
            # Use Groq to generate contextual message
            issue_dict = {
                "title": issue.title,
                "description": issue.description,
                "severity": issue.severity,
                "issue_type": issue.issue_type,
                "ai_analysis": issue.ai_analysis,
                "status": issue.status
            }
            
            return self.groq_service.create_notification_message(issue_dict, channel)
            
        except Exception as e:
            logger.error(f"Error creating notification message: {e}")
            # Fallback message
            return f"""
Issue: {issue.title}
Description: {issue.description}
Severity: {issue.severity.upper()}
Status: {issue.status.upper()}

Please review this issue and take appropriate action.
            """.strip()
    
    async def _save_notification(self, notification_type: str, recipient: str, subject: str, 
                               message: str, issue_id: int) -> Dict[str, Any]:
        """Save notification record to database"""
        try:
            db = SessionLocal()
            
            notification = Notification(
                notification_type=notification_type,
                recipient=recipient,
                subject=subject,
                message=message,
                status="sent",
                related_issue_id=issue_id
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            return notification.to_dict()
            
        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            if db:
                db.rollback()
            return {}
        finally:
            if db:
                db.close()
    
    async def send_reminder_notifications(self) -> List[Dict[str, Any]]:
        """Send reminder notifications for unresolved issues"""
        logger.info("Starting reminder notifications...")
        
        try:
            db = SessionLocal()
            
            # Get issues that have been open for more than 24 hours
            reminder_threshold = datetime.utcnow() - timedelta(hours=24)
            
            issues = db.query(PipelineIssue).filter(
                PipelineIssue.status.in_(["open", "investigating"]),
                PipelineIssue.detected_at < reminder_threshold
            ).all()
            
            reminders_sent = []
            
            for issue in issues:
                # Check if we sent a reminder in the last 6 hours
                recent_reminder = db.query(Notification).filter(
                    Notification.related_issue_id == issue.id,
                    Notification.subject.like("%REMINDER%"),
                    Notification.sent_at > datetime.utcnow() - timedelta(hours=6)
                ).first()
                
                if recent_reminder:
                    continue
                
                # Send reminder
                reminder_message = f"""
REMINDER: This issue has been open for more than 24 hours.

{issue.title}
{issue.description}

Please take action to resolve this issue.
                """.strip()
                
                # Send reminder via primary channel
                if self.config.notifications.slack_webhook:
                    notification = await self._send_slack_reminder(issue, reminder_message)
                    if notification:
                        reminders_sent.append(notification)
                elif self.config.notifications.email_smtp:
                    notification = await self._send_email_reminder(issue, reminder_message)
                    if notification:
                        reminders_sent.append(notification)
            
            db.close()
            
            logger.info(f"Reminder notifications completed. Sent {len(reminders_sent)} reminders.")
            return reminders_sent
            
        except Exception as e:
            logger.error(f"Error in reminder notifications: {e}")
            return []
    
    async def _send_slack_reminder(self, issue: PipelineIssue, message: str) -> Optional[Dict[str, Any]]:
        """Send reminder notification to Slack"""
        try:
            payload = {
                "attachments": [
                    {
                        "color": "#ffcc00",  # Yellow for reminders
                        "title": f"⏰ REMINDER: {issue.title}",
                        "text": message,
                        "footer": "DevSecOps AI Monitoring - Reminder",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.config.notifications.slack_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                notification = await self._save_notification(
                    "slack",
                    "DevSecOps Team",
                    f"REMINDER: {issue.title}",
                    message,
                    issue.id
                )
                return notification
            
            return None
            
        except Exception as e:
            logger.error(f"Error sending Slack reminder: {e}")
            return None
    
    async def _send_email_reminder(self, issue: PipelineIssue, message: str) -> Optional[Dict[str, Any]]:
        """Send reminder notification via email"""
        try:
            subject = f"REMINDER: {issue.title}"
            
            if self.config.notifications.email_smtp and self.config.notifications.email_user and self.config.notifications.email_password:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.config.notifications.email_user
                msg['To'] = self.config.notifications.email_user
                
                html_content = f"""
                <html>
                <body>
                    <div style="background-color: #ffcc00; padding: 15px; border-radius: 5px;">
                        <h2>⏰ REMINDER: {issue.title}</h2>
                    </div>
                    <div style="margin: 20px 0;">
                        <p>{message}</p>
                    </div>
                    <div style="font-size: 12px; color: #666;">
                        <p>This is an automated reminder from DevSecOps AI Monitoring System.</p>
                    </div>
                </body>
                </html>
                """
                
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
                
                server = smtplib.SMTP(self.config.notifications.email_smtp, 587)
                server.starttls()
                server.login(self.config.notifications.email_user, self.config.notifications.email_password)
                server.send_message(msg)
                server.quit()
                
                notification = await self._save_notification(
                    "email",
                    self.config.notifications.email_user,
                    subject,
                    message,
                    issue.id
                )
                return notification
            
            return None
            
        except Exception as e:
            logger.error(f"Error sending email reminder: {e}")
            return None
    
    async def run(self) -> Dict[str, Any]:
        """Main entry point for the notification agent"""
        logger.info("Starting Notification Agent...")
        
        start_time = datetime.utcnow()
        
        try:
            # Send regular notifications
            notifications = await self.send_notifications()
            
            # Send reminder notifications
            reminders = await self.send_reminder_notifications()
            
            # Generate summary
            summary = {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "notifications_sent": len(notifications),
                "reminders_sent": len(reminders),
                "total_sent": len(notifications) + len(reminders),
                "notifications": notifications,
                "reminders": reminders,
                "status": "completed"
            }
            
            logger.info(f"Notification Agent completed. Sent {summary['total_sent']} notifications.")
            return summary
            
        except Exception as e:
            logger.error(f"Error in Notification Agent: {e}")
            return {
                "agent_name": self.name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            } 