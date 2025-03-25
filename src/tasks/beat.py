import asyncio

from src.tasks.app import app
from src.tasks.tasks import clear_outdated_links_task


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        10.0,
        clear_outdated_links_task.s(),
        name="clear_outdated_links",
    )

