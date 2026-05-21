from concurrent.futures import ThreadPoolExecutor

from datapizza.clients.openai import OpenAIClient
from datapizza.memory import Memory
from datapizza.tools import Tool
from datapizza.type import ROLE, Block, FunctionCallBlock, FunctionCallResultBlock
from datapizza.type.type import TextBlock

from workshop.custom_logs import log_answer, log_tool_call_invoke, log_tool_call_result


class Agent:
    def __init__(
        self,
        client: OpenAIClient,
        system_prompt: str,
        tools: list[Tool],
        compact_logs: bool = False,
        max_tool_workers: int = 8,
        name: str = "",
    ):
        # TODO: Store tools in a mapping by tool name so function calls can be executed.
        self.tool_mapping = {}
        self.tools = tools
        self.client = client
        self.memory = Memory()
        self.tool_executor = ThreadPoolExecutor(max_workers=max_tool_workers)
        self.system_prompt = system_prompt
        self.compact_logs = compact_logs
        self.name = name

    def _execute_tool_call(
        self,
        block: FunctionCallBlock,
    ) -> FunctionCallResultBlock:
        # TODO: Look up the requested tool from self.tool_mapping.
        # TODO: Log the tool invocation with log_tool_call_invoke.
        # TODO: Execute the tool with block.arguments.
        # TODO: Log the tool result with log_tool_call_result.
        # TODO: Return a FunctionCallResultBlock with the original call id.
        raise NotImplementedError

    def _step(
        self, input: str | None = None, memory: Memory | None = None
    ) -> tuple[list[Block], list[FunctionCallResultBlock]]:
        # TODO: Invoke the model with input, tools, memory, and system_prompt.
        # TODO: Collect response blocks.
        # TODO: Submit each FunctionCallBlock to self.tool_executor.
        # TODO: Log TextBlock answers with log_answer.
        # TODO: Return response blocks plus completed tool results.
        raise NotImplementedError

    def run(self, input: str) -> str:
        # TODO: Add the user input to memory as ROLE.USER.
        # TODO: Loop model steps until no tool calls are returned.
        # TODO: Add assistant response blocks as ROLE.ASSISTANT.
        # TODO: Add each tool result separately as ROLE.TOOL.
        # TODO: Return the final text response.
        raise NotImplementedError
