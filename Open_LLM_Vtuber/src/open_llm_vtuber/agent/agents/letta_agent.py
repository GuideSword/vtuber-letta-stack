from datetime import datetime
from typing import AsyncIterator, List, Dict, Any
from .agent_interface import AgentInterface
from ..output_types import SentenceOutput
from ..transformers import (
    sentence_divider,
    actions_extractor,
    tts_filter,
    display_processor,
)
from ...config_manager import TTSPreprocessorConfig
from ..input_types import BatchInput, TextSource
from letta_client import Letta
from ...computer_control.artifacts import COMPUTER_CONTROL_ARTIFACT_ROOT
from ...computer_control.bridge import ComputerControlBridge
from ...computer_control.intent import detect_computer_control_intent
from .letta_tool_formatter import (
    extract_tool_media_for_user,
    format_tool_return_for_user,
)


class LettaAgent(AgentInterface):
    """
    Custom Letta class to interface with the Letta server.
    """

    def __init__(
        self,
        live2d_model,
        id,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        host: str = "localhost",
        port: int = 8283,
    ):
        super().__init__()
        self.url = f"http://{host}:{port}"
        self.client = Letta(base_url=self.url)
        self.id = id
        self._computer_control_bridge = ComputerControlBridge()
        # Initialize decorator parameters
        self._tts_preprocessor_config = tts_preprocessor_config
        self._live2d_model = live2d_model
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method

        # Delay decorator application
        self.chat = tts_filter(self._tts_preprocessor_config)(
            display_processor()(
                actions_extractor(self._live2d_model)(
                    sentence_divider(
                        faster_first_response=self._faster_first_response,
                        segment_method=self._segment_method,
                        valid_tags=["think"],
                    )(self.chat)
                )
            )
        )

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        # The Letta Server automatically stores historical messages, so this part is not needed
        pass

    def handle_interrupt(self, heard_response: str) -> None:
        pass

    async def generator_to_async(self, gen):
        for item in gen:
            yield item

    def _format_tool_return(self, tool_return) -> str | None:
        tool_return_str = str(tool_return)
        error_keywords = ["Error executing function", "No function named", "KeyError"]
        if any(keyword in tool_return_str for keyword in error_keywords):
            return None
        return format_tool_return_for_user(tool_return) or tool_return_str

    def _tool_media_messages(self, tool_return) -> list[dict[str, object]]:
        return [
            {
                "type": "chat-media",
                "media_type": item["type"],
                "url": item["url"],
                "caption": item.get("caption", ""),
                "browser_view": {
                    "debuggerFullscreenUrl": item["url"],
                    "title": item.get("caption", "Browser screenshot"),
                },
            }
            for item in extract_tool_media_for_user(tool_return)
        ]

    def _local_intent_arguments(self, local_intent) -> dict[str, object]:
        arguments = dict(local_intent.arguments)
        if (
            local_intent.action == "browser_screenshot"
            and not arguments.get("path")
            and not arguments.get("output_path")
        ):
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            arguments["path"] = str(
                COMPUTER_CONTROL_ARTIFACT_ROOT / f"browser-screenshot-{timestamp}.png"
            )
        return arguments

    async def chat(self, input_data: BatchInput) -> AsyncIterator[SentenceOutput]:
        import sys
        
        local_intent = detect_computer_control_intent(self._to_text_prompt(input_data))
        if local_intent:
            arguments = self._local_intent_arguments(local_intent)
            print(
                f"[Letta Agent] Running local computer_control intent: {local_intent.action} {arguments}",
                file=sys.stderr,
            )
            result = self._computer_control_bridge.execute(
                local_intent.action,
                arguments,
                requested_by="local_intent",
            )
            tool_return = result.to_dict()
            tool_return_text = self._format_tool_return(tool_return)
            if tool_return_text:
                yield tool_return_text
            for media_message in self._tool_media_messages(tool_return):
                yield media_message
            return

        messages = self._to_messages(input_data)
        print(f"[Letta Agent] Sending messages to Letta: {messages}", file=sys.stderr)
        
        try:
            print(f"[Letta Agent] Creating stream for agent: {self.id}", file=sys.stderr)
            # 尝试使用流式API
            print("[Letta Agent] Using streaming API...", file=sys.stderr)
            stream = self.client.agents.messages.create_stream(
                agent_id=self.id,
                messages=messages,
                stream_tokens=False,
            )

            complete_response = ""
            print("[Letta Agent] Starting to receive tokens", file=sys.stderr)
            
            # 遍历流式响应
            for token in stream:
                print(f"[Letta Agent] Received token: {token}", file=sys.stderr)
                print(f"[Letta Agent] Token type: {type(token)}", file=sys.stderr)
                
                # 检查token是否有message_type属性
                if hasattr(token, 'message_type'):
                    print(f"[Letta Agent] Message type: {token.message_type}", file=sys.stderr)
                    
                    # 尝试从各种可能的属性中获取内容
                    if hasattr(token, 'content') and token.content:
                        print(f"[Letta Agent] Found content: {token.content}", file=sys.stderr)
                        # 过滤掉额外的信息，只保留实际回复
                        content = token.content
                        # 移除request_heartbeat等额外信息
                        if ',' in content and 'request_heartbeat' in content:
                            content = content.split(',')[0].strip()
                        # 过滤掉系统消息
                        if '[This is an automated system message hidden from the user]' in content:
                            print(f"[Letta Agent] Filtering out system message", file=sys.stderr)
                        else:
                            yield content
                            complete_response += content
                    # 跳过reasoning内容和错误消息，只保留实际回复
                    elif hasattr(token, 'tool_return') and token.tool_return:
                        print(f"[Letta Agent] Found tool_return: {token.tool_return}", file=sys.stderr)
                        # 跳过错误消息
                        tool_return_text = self._format_tool_return(token.tool_return)
                        if not tool_return_text:
                            print(f"[Letta Agent] Filtering out error message", file=sys.stderr)
                        else:
                            yield tool_return_text
                            complete_response += tool_return_text
                            for media_message in self._tool_media_messages(token.tool_return):
                                yield media_message
                    else:
                        print(f"[Letta Agent] No content found in token with type: {token.message_type}", file=sys.stderr)
                else:
                    # 如果token没有message_type属性，尝试直接获取内容
                    print(f"[Letta Agent] Token without message_type: {token}", file=sys.stderr)
                    
                    # 尝试从其他可能的属性中获取内容
                    if hasattr(token, 'content') and token.content:
                        print(f"[Letta Agent] Found content attribute: {token.content}", file=sys.stderr)
                        # 过滤掉系统消息
                        content = token.content
                        if '[This is an automated system message hidden from the user]' in content:
                            print(f"[Letta Agent] Filtering out system message", file=sys.stderr)
                        else:
                            yield content
                            complete_response += content
                    elif hasattr(token, 'reasoning') and token.reasoning:
                        print(f"[Letta Agent] Found reasoning attribute: {token.reasoning}", file=sys.stderr)
                        # 跳过reasoning内容
                        print(f"[Letta Agent] Skipping reasoning content", file=sys.stderr)
                    elif hasattr(token, 'tool_return') and token.tool_return:
                        print(f"[Letta Agent] Found tool_return attribute: {token.tool_return}", file=sys.stderr)
                        # 跳过错误消息
                        tool_return_text = self._format_tool_return(token.tool_return)
                        if not tool_return_text:
                            print(f"[Letta Agent] Filtering out error message", file=sys.stderr)
                        else:
                            yield tool_return_text
                            complete_response += tool_return_text
                            for media_message in self._tool_media_messages(token.tool_return):
                                yield media_message
                    else:
                        # 尝试将整个token转换为字符串
                        token_str = str(token)
                        if token_str and len(token_str) > 0:
                            print(f"[Letta Agent] Using token as string: {token_str}", file=sys.stderr)
                            yield token_str
                            complete_response += token_str
                        else:
                            print(f"[Letta Agent] No content found in token", file=sys.stderr)
                    
                print(f"[Letta Agent] Current response: {complete_response}", file=sys.stderr)
            
            print(f"[Letta Agent] Complete response: {complete_response}", file=sys.stderr)
            
        except Exception as e:
            print(f"[Letta Agent] Error in chat method: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            
            # 发生错误时，返回错误信息
            error_message = f"[Error] {str(e)}"
            yield error_message
            print(f"[Letta Agent] Yielded error message: {error_message}", file=sys.stderr)

    def _to_text_prompt(self, input_data: BatchInput) -> str:
        """
        Format BatchInput into a prompt string for the LLM.

        Args:
            input_data: BatchInput - The input data containing texts

        Returns:
            str - Formatted message string
        """
        message_parts = []

        # Process text inputs in order
        for text_data in input_data.texts:
            if text_data.source == TextSource.INPUT:
                message_parts.append(text_data.content)
            elif text_data.source == TextSource.CLIPBOARD:
                message_parts.append(f"[Clipboard content: {text_data.content}]")

        return "\n".join(message_parts)

    def _to_messages(self, input_data: BatchInput) -> List[Dict[str, Any]]:
        """
        Prepare messages list without image support.
        """
        messages = []

        if input_data.images:
            content = []
            text_content = self._to_text_prompt(input_data)
            content.append({"type": "text", "text": text_content})
            user_message = {"role": "user", "content": content}
        else:
            user_message = {"role": "user", "content": self._to_text_prompt(input_data)}

        messages.append(user_message)

        return messages
