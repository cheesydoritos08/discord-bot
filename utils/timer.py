import asyncio
import handlers.database_handler as database_handler

class Timer():
    # Sets variables for the timer
    def __init__(self, user_id, name, starttime, timer_length):
        self.user_id = user_id
        self.name = name
        self.start_time = starttime
        self.timer_length = timer_length

    def create_timer(self):
        async def new_timer():
            await asyncio.sleep(self.timer_length)
            self.complete_task()

        # Sets the timer on the user profile to corresponding timerd
        database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": (self.start_time + self.timer_length)}})
        asyncio.create_task(new_timer())

    # Finishes the tasks based off of their nails
    def complete_task(self):        
        if self.name == "won_booster":
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"buffs.{self.name}.active": False}})
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"buffs.{self.name}.multiplier": 0}})
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": 0}})   
        elif self.name == "xp_booster":
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"buffs.{self.name}.active": False}})
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"buffs.{self.name}.multiplier": 0}})
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": 0}})  
        elif self.name == "daily_claim":
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": 0}})  
        elif self.name == "daily_quests":
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {"quests": []}})  
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {"all_quests_complete": False}})  
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": 0}}) 
        elif self.name == "daily_claim":
            database_handler.users.update_one({"_id": self.user_id}, {"$set": {f"timers.{self.name}": 0}})  


