# Email Integration System

## 1. Email Configuration Storage

```python
# app/utils/email_utils.py
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import smtplib
import sqlite3
from pathlib import Path
import json

class EmailConfig:
    def __init__(self, db):
        self.db = db
        self._ensure_table()
    
    def _ensure_table(self):
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS email_config (
                id INTEGER PRIMARY KEY,
                smtp_server TEXT NOT NULL,
                smtp_port INTEGER NOT NULL,
                use_ssl BOOLEAN NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                default_from TEXT NOT NULL
            )
        ''')
        self.db.commit()
    
    def save_config(self, config):
        self.db.execute('''
            INSERT OR REPLACE INTO email_config 
            (id, smtp_server, smtp_port, use_ssl, username, password, default_from)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (
            config['smtp_server'],
            config['smtp_port'],
            config['use_ssl'],
            config['username'],
            config['password'],
            config['default_from']
        ))
        self.db.commit()
    
    def get_config(self):
        result = self.db.execute('SELECT * FROM email_config WHERE id = 1').fetchone()
        if result:
            return dict(result)
        return None

class EmailSender:
    def __init__(self, db, image_manager):
        self.config = EmailConfig(db)
        self.image_manager = image_manager
    
    def send_job_images(self, job_id, recipient, message_text, image_ids=None):
        config = self.config.get_config()
        if not config:
            raise ValueError("Email not configured")
            
        msg = MIMEMultipart()
        msg['From'] = config['default_from']
        msg['To'] = recipient
        msg['Subject'] = f"Job Images - {job_id}"
        
        # Add text body
        msg.attach(MIMEText(message_text))
        
        # Get images
        images = self.db.execute('''
            SELECT * FROM job_image 
            WHERE job_id = ? 
            AND (? IS NULL OR id IN (%s))
        ''' % ','.join('?' * len(image_ids)) if image_ids else ')',
            [job_id] + (image_ids if image_ids else []))
        
        # Attach images
        for img in images:
            image_path = self.image_manager.get_image_path(job_id, img['filename'])
            with open(image_path, 'rb') as f:
                img_attach = MIMEImage(f.read())
                img_attach.add_header('Content-Disposition', 'attachment', 
                                    filename=img['filename'])
                msg.attach(img_attach)
        
        # Send email
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            if config['use_ssl']:
                server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
```

## 2. Configuration Routes

```python
# app/routes/settings_routes.py
from flask import Blueprint, request, jsonify
from ..utils.email_utils import EmailConfig

bp = Blueprint('settings', __name__)

@bp.route('/email/config', methods=['GET', 'POST'])
@with_db
def email_config(db):
    config = EmailConfig(db)
    
    if request.method == 'POST':
        data = request.json
        try:
            # Test connection before saving
            with smtplib.SMTP(data['smtp_server'], data['smtp_port']) as server:
                if data['use_ssl']:
                    server.starttls()
                server.login(data['username'], data['password'])
            
            config.save_config(data)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    current_config = config.get_config()
    if current_config:
        current_config['password'] = '********'  # Don't send actual password
    return jsonify(current_config)
```

## 3. Email Templates

```python
# app/utils/email_templates.py
class EmailTemplates:
    @staticmethod
    def job_images(job, images):
        return f"""
Dear Client,

Please find attached images from job {job['id']}: {job['description']}.

Number of images: {len(images)}

Best regards,
{job['customer_name']}
        """
```

## 4. UI Integration

```html
<!-- settings.html -->
<div class="form-section">
    <h3>Email Configuration</h3>
    <form id="emailConfigForm">
        <div class="form-group">
            <label>SMTP Server</label>
            <select name="smtp_preset" onchange="updateSmtpSettings(this.value)">
                <option value="">Custom</option>
                <option value="gmail">Gmail</option>
                <option value="outlook">Outlook</option>
            </select>
        </div>
        
        <div class="form-group">
            <label>SMTP Server</label>
            <input type="text" name="smtp_server" required>
        </div>
        
        <div class="form-group">
            <label>SMTP Port</label>
            <input type="number" name="smtp_port" required>
        </div>
        
        <div class="form-group">
            <label>
                <input type="checkbox" name="use_ssl">
                Use SSL/TLS
            </label>
        </div>
        
        <div class="form-group">
            <label>Email</label>
            <input type="email" name="username" required>
        </div>
        
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        
        <button type="submit" class="action-btn save-btn">Save Configuration</button>
        <button type="button" onclick="testEmail()" class="action-btn">Test Connection</button>
    </form>
</div>

<script>
const smtpPresets = {
    gmail: {
        smtp_server: 'smtp.gmail.com',
        smtp_port: 587,
        use_ssl: true
    },
    outlook: {
        smtp_server: 'smtp.office365.com',
        smtp_port: 587,
        use_ssl: true
    }
};

function updateSmtpSettings(preset) {
    if (preset && smtpPresets[preset]) {
        const settings = smtpPresets[preset];
        document.querySelector('[name=smtp_server]').value = settings.smtp_server;
        document.querySelector('[name=smtp_port]').value = settings.smtp_port;
        document.querySelector('[name=use_ssl]').checked = settings.use_ssl;
    }
}
</script>

<!-- job_details.html (addition) -->
<div class="btn-group">
    <button onclick="showEmailDialog()" class="action-btn">Email Images</button>
</div>

<div id="emailDialog" class="modal">
    <div class="modal-content">
        <h3>Send Images</h3>
        <form id="emailForm">
            <div class="form-group">
                <label>Recipient Email</label>
                <input type="email" name="recipient" required>
            </div>
            
            <div class="form-group">
                <label>Message</label>
                <textarea name="message"></textarea>
            </div>
            
            <div class="image-selection">
                {% for image in images %}
                <div class="image-item">
                    <input type="checkbox" name="selected_images[]" value="{{ image.id }}">
                    <img src="{{ url_for('job.serve_image', 
                                        job_id=job.id, 
                                        filename=image.filename,
                                        thumbnail=true) }}">
                </div>
                {% endfor %}
            </div>
            
            <div class="btn-group">
                <button type="submit" class="action-btn save-btn">Send</button>
                <button type="button" onclick="closeEmailDialog()" class="action-btn cancel-btn">Cancel</button>
            </div>
        </form>
    </div>
</div>
```

## 5. Common Email Provider Settings

Here are some common settings for popular email providers:

### Gmail
- Server: smtp.gmail.com
- Port: 587
- SSL/TLS: Yes
- Note: Requires "App Password" if 2FA is enabled

### Outlook/Office 365
- Server: smtp.office365.com
- Port: 587
- SSL/TLS: Yes

### Custom Email Server
For users with their own email server or hosting provider, they'll need:
- SMTP server address
- Port number
- SSL/TLS requirements
- Username/password

## 6. Security Considerations

1. Password Storage:
   - Passwords are stored in the database
   - Consider encrypting sensitive data
   - Option to store in environment variables

2. Email Security:
   - Always use SSL/TLS
   - Validate email addresses
   - Rate limit sending
   - Log all email activities

3. Best Practices:
   - Limit image sizes in emails
   - Option to send download links instead
   - Automatic retry for failed sends

## 7. Fallback Options

1. Direct Email:
   - Open default email client with images attached
   - Uses mailto: protocol
   - No credentials needed but less integrated

2. Export to ZIP:
   - Create ZIP file of selected images
   - User can attach to their own email
   - Good fallback if email setup fails

