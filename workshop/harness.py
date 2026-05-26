import weakref
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from datapizza.clients.openai import OpenAIClient
from datapizza.memory import Memory
from datapizza.tools import Tool
from datapizza.type import ROLE, Block, FunctionCallBlock, FunctionCallResultBlock
from datapizza.type.type import TextBlock

from workshop.custom_logs import (
    log_answer,
    log_event,
    log_tool_call_invoke,
    log_tool_call_result,
)


class Agent:
    def __init__(
        self,
        client: OpenAIClient,
        system_prompt: str,
        tools: list[Tool],
        compact_logs: bool = False,
        max_tool_workers: int = 8,
        name: str = "",
        tool_timeout: float | None = None,
    ):
        self.tool_mapping = {tool.name: tool for tool in tools}
        self.tools = tools
        self.client = client
        self.memory = Memory()
        self.tool_executor = ThreadPoolExecutor(max_workers=max_tool_workers)
        self.system_prompt = system_prompt
        self.compact_logs = compact_logs
        self.name = name
        self.tool_timeout = tool_timeout
        weakref.finalize(self, self.tool_executor.shutdown, wait=False)

    def _error_result(
        self, block: FunctionCallBlock, message: str
    ) -> FunctionCallResultBlock:
        log_event(
            "tool_error",
            f"{block.name}: {message}",
            color="red",
            agent_name=self.name,
        )
        return FunctionCallResultBlock(
            id=block.id,
            tool=self.tool_mapping.get(block.name),
            result=f"<tool error: {message}>",
        )

    def _execute_tool_call(
        self,
        block: FunctionCallBlock,
    ) -> FunctionCallResultBlock:
        tool = self.tool_mapping[block.name]

        log_tool_call_invoke(
            block.name,
            block.arguments,
            compact=self.compact_logs,
            agent_name=self.name,
        )
        try:
            result = tool(**block.arguments)
        except Exception as e:
            return self._error_result(block, f"{type(e).__name__}: {e}")
        log_tool_call_result(
            block.name,
            result,
            compact=self.compact_logs,
            agent_name=self.name,
        )

        return FunctionCallResultBlock(
            id=block.id,
            tool=tool,
            result=result,
        )

    def _step(
        self, input: str | None = None, memory: Memory | None = None
    ) -> tuple[list[Block], list[FunctionCallResultBlock]]:
        response = self.client.invoke(
            input=input,
            tools=list(self.tool_mapping.values()),
            memory=memory,
            system_prompt=self.system_prompt,
        )

        response_blocks: list[Block] = []
        pending: list[tuple[FunctionCallBlock, Future]] = []
        for block in response.content:
            response_blocks.append(block)
            if isinstance(block, FunctionCallBlock):
                pending.append(
                    (block, self.tool_executor.submit(self._execute_tool_call, block))
                )
            elif isinstance(block, TextBlock):
                log_answer(
                    block.content,
                    compact=self.compact_logs,
                    agent_name=self.name,
                )

        tool_results: list[FunctionCallResultBlock] = []
        for block, future in pending:
            try:
                tool_results.append(future.result(timeout=self.tool_timeout))
            except FuturesTimeoutError:
                future.cancel()
                tool_results.append(
                    self._error_result(block, f"timeout after {self.tool_timeout}s")
                )
        return response_blocks, tool_results

    def run(self, input: str) -> str:
        self.memory.add_turn(TextBlock(content=input), ROLE.USER)
        while True:
            response_blocks, tool_results = self._step(memory=self.memory)
            self.memory.add_turn(response_blocks, ROLE.ASSISTANT)
            if tool_results:
                for tool_result in tool_results:
                    self.memory.add_turn(tool_result, ROLE.TOOL)
                continue
            return "".join(
                block.content
                for block in response_blocks
                if isinstance(block, TextBlock)
            )
