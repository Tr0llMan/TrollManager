# Discord Bot with Dynamic Configuration and Notifications

This Discord bot provides a range of automated features, including dynamic voice channel management, YouTube video notifications, Twitch stream notifications, and easy-to-use slash commands for configuration.

## Features

### 1. **Dynamic Voice Channels**
- Automatically creates temporary voice channels when users join specified trigger channels.
- Deletes the temporary voice channels after a configurable period of inactivity.
- Fully customizable using the `/set_dynamicvc` command.

### 2. **YouTube Video Notifications**
- Detects new YouTube videos or live streams from a specific channel.
- Sends custom notifications based on video titles and associated keywords.
- Configurable roles for video notifications via the `/add_youtube` command.

### 3. **Twitch Stream Notifications**
- Detects when specified Twitch streamers go live.
- Sends live stream alerts to a designated Discord channel.
- Configurable Twitch streamers and roles via the `/add_streamer` command.

### 4. **Slash Commands**
#### Slash commands make it easy to configure the bot:
- `/set_dynamicvc`: Configure dynamic voice channels with trigger channels, roles, and categories.
- `/read_config`: Display the current bot configuration.
- `/set_inactivity_time`: Set the maximum inactivity time for dynamic voice channels.
- `/add_streamer`: Add a Twitch streamer for notifications.
- `/add_youtube`: Add a YouTube keyword and role for notifications.

## Getting Started

### Prerequisites
- Python 3.9+
- Discord Bot Token
- YouTube Data API Key
- Twitch Client ID and Client Secret

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**
   Create a `.env` file in the root directory and add the following:
   ```env
   DISCORD_BOT_TOKEN=your_discord_bot_token
   GOOGLE_API_KEY=your_youtube_api_key
   TWITCH_CLIENT_ID=your_twitch_client_id
   TWITCH_CLIENT_SECRET=your_twitch_client_secret
   TWITCH_USERNAME=your_twitch_username
   YOUTUBE_CHANNEL_ID=your_youtube_channel_id
   DISCORD_NOTIFICATION_CHANNEL_ID=your_discord_channel_id
   GUILD_ID=your_guild_id
   DYNAMIC_CATEGORY_ID=your_dynamic_category_id
   ```

4. **Run the Bot**
   ```bash
   python bot.py
   ```

## Slash Commands

### `/set_dynamicvc`
**Description**: Configure dynamic voice channels.
- **Parameters**:
  - `host_category`: The category containing trigger channels.
  - `dynamic_category`: The category where temporary VCs will be created.
  - `vc_ids`: Comma-separated list of VC IDs.
  - `roles`: Comma-separated list of associated role IDs.
- **Example**:
  ```
  /set_dynamicvc [Host Category] [Dynamic Category] [VC IDs: 1234,5678] [Roles: 9876,4321]
  ```

### `/read_config`
**Description**: Display the current bot configuration.
- **Example**:
  ```
  /read_config
  ```

### `/set_inactivity_time`
**Description**: Set the maximum inactivity time for dynamic VCs.
- **Parameters**:
  - `time`: Maximum inactivity time in seconds.
- **Example**:
  ```
  /set_inactivity_time 300
  ```

### `/add_streamer`
**Description**: Add a Twitch streamer for notifications.
- **Parameters**:
  - `username`: Twitch username.
  - `role`: Role ID for notifications.
- **Example**:
  ```
  /add_streamer Tr0lIMan 123456789012345678
  ```

### `/add_youtube`
**Description**: Add a YouTube keyword and associated role.
- **Parameters**:
  - `keyword`: Keyword to look for in video titles.
  - `role`: Role ID for notifications.
- **Example**:
  ```
  /add_youtube Overwatch 2 987654321098765432
  ```

## Configuration Management

### Dynamic VCs
- Trigger channels and roles are managed using `/set_dynamicvc`.
- Maximum inactivity time can be updated using `/set_inactivity_time`.

### YouTube Notifications
- Add new keywords and roles for custom notifications with `/add_youtube`.

### Twitch Notifications
- Add new Twitch streamers and associated roles with `/add_streamer`.

## Logging
- Logs are saved to `bot.log` in the root directory.
- Logs include command usage, errors, and important events.

## Contributing
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -m 'Add new feature'`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

Happy coding! 🎉

