import pandas
import authenticate
import requests
import matplotlib.pyplot as plt
import io
from PIL import Image, ImageDraw, ImageFont
import textwrap
import yaml
from datetime import datetime
import matplotlib.dates as mdates
import platform
from zoneinfo import ZoneInfo


class Strava:
    def __init__(self):
        self._access_token = authenticate.get_strava_access_token()
        self.headers = {'Authorization': 'Bearer ' + self._access_token}

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
            self._athlete_id = config.get("athlete_id")
            self.urls = config.get("urls", {})
            self.icons = config.get("icons", {})
            self.goals = config.get("goals", {})
            # Detect OS
            if platform.system() == "Windows":
                self.bold_font_path = config.get("bold_font_path_windows")
                self.regular_font_path = config.get("regular_font_path_windows")
            else:
                self.bold_font_path = config.get("bold_font_path_linux")
                self.regular_font_path = config.get("regular_font_path_linux")
            self._input_data = config.get("input_data")
            self._race_image_path = config.get("race_image_path")

        self.activities = self.get_activities()
        self.recent_stats = self.get_recent_stats()
        self.race_calendar = pandas.read_excel(self._input_data, sheet_name="race_calendar")


    def get_activities(self, n: int=200) -> pandas.DataFrame:
        """
        Returns the last n activities
        """
        param = {'per_page': n, 'page': 1}
        activities = requests.get(self.urls["activities"], headers=self.headers, params=param).json()
        activities = pandas.json_normalize(activities)
        return activities

    def get_latest_ids(self) -> dict[str, int]:
        """
        Returns the activity id of the latest run, ride
        TODO: Fetch latest race
        """
        ids = self.activities.sort_values(by="start_date", ascending=False).groupby("sport_type")["id"].first()
        return ids[ids.index.isin(["Run", "VirtualRide"])].to_dict()

    # def get_heart_rate_zones(self, activity_id: int) -> bytes:
    #     zones = requests.get(f'{self.urls["individual_activity"]}/{activity_id}/zones', headers=self.headers).json()
    #     zones = zones[0]['distribution_buckets']  # Filter for default heart rate zones
    #     values = []
    #     for zone in zones:
    #         values.append(zone['time'])
    #
    #     colors = matplotlib.colors.LinearSegmentedColormap.from_list("light_to_dark_red", ["lightcoral", "darkred"], N=len(values))
    #     segment_colors = [colors(i) for i in range(len(values))]
    #     plt.figure(figsize=(8, 4.8))
    #     plt.pie(values, colors=segment_colors, startangle=90, counterclock=False)
    #
    #     img_buffer = io.BytesIO()
    #     plt.savefig(img_buffer, format="jpg", dpi=300)
    #     # plt.savefig("output/pie_chart.jpg", format="jpg", dpi=300)
    #     plt.close()
    #     img_buffer.seek(0)
    #
    #     return img_buffer.getvalue()

    def get_recent_stats(self) -> dict[str, float]:
        stats = requests.get(f'{self.urls["athlete_stats"]}/{self._athlete_id}/stats', headers=self.headers).json()
        stats = pandas.json_normalize(stats)
        return stats.iloc[0].to_dict()


    # @staticmethod
    # def get_polyline(details) -> bytes:
    #     summary_polyline = details["map"]["summary_polyline"]
    #     decoded_polyline = polyline.decode(summary_polyline)
    #     # start_latlng = details["start_latlng"]
    #     # my_map = folium.Map(location=[start_latlng[0], start_latlng[1]], zoom_start=14)
    #     # folium.PolyLine(decoded_polyline, color="blue", weight=2.5, opacity=1).add_to(my_map)
    #     # my_map.save("output/polyline.html")
    #
    #     # Separate latitudes and longitudes
    #     latitudes = [point[0] for point in decoded_polyline]
    #     longitudes = [point[1] for point in decoded_polyline]
    #     plt.figure(figsize=(6, 6))
    #     plt.plot(longitudes, latitudes, linestyle='-', color='orange')
    #
    #     # Remove the borders (spines) and axes
    #     plt.gca().get_xaxis().set_visible(False)
    #     plt.gca().get_yaxis().set_visible(False)
    #     for spine in plt.gca().spines.values():
    #         spine.set_visible(False)
    #
    #     img_buffer = io.BytesIO()
    #     plt.savefig(img_buffer, format="jpg", dpi=300)
    #     # plt.savefig("output/polyline.jpg", format="jpg", dpi=300)
    #     plt.close()
    #     img_buffer.seek(0)
    #
    #     return img_buffer.getvalue()


    # def get_detailed_run(self) -> None:
    #     run_id = self.get_latest_ids()["Run"]
    #
    #     param = {'include_all_efforts': False}
    #     # run_id = 13226803155  # Not treadmill
    #     heart_rate_zone_bytes = self.get_heart_rate_zones(activity_id=run_id)
    #     details = requests.get(f'{self.urls["individual_activity"]}/{run_id}', headers=self.headers, params=param).json()
    #     if details["map"]:
    #         polyline_bytes = self.get_polyline(details=details)
    #
    #         polyline_buffer = io.BytesIO(polyline_bytes)
    #         heart_rate_zone_buffer = io.BytesIO(heart_rate_zone_bytes)
    #
    #         polyline_buffer.seek(0)
    #         heart_rate_zone_buffer.seek(0)
    #
    #         polyline_image = Image.open(polyline_buffer)
    #         heart_rate_zone = Image.open(heart_rate_zone_buffer)
    #         new_width = polyline_image.width + heart_rate_zone.width
    #         new_height = max(polyline_image.height, heart_rate_zone.height)
    #
    #         screen = Image.new('RGB', (new_width, new_height))
    #         screen.paste(polyline_image, (0, 0))
    #         screen.paste(heart_rate_zone, (polyline_image.width, 0))
    #         resized_screen = screen.resize((800, 480), Image.Resampling.LANCZOS)
    #         resized_screen.save("output/screen1.jpg", format="JPEG", quality=70, progressive=False)

    def progress_ring(self, image: Image, center: tuple, outer_radius: float, progress: float, icon: str) -> None:
        """
        Generates a progress ring based on the progress % with the icon in the middle
        """
        draw = ImageDraw.Draw(image)
        start_angle = -90
        end_angle = start_angle + (progress * 360)
        # Draw full border
        draw.arc([center[0] - outer_radius, center[1] - outer_radius, center[0] + outer_radius,
                  center[1] + outer_radius],
                 start=0, end=360, fill="grey", width=20)

        # Shade progress
        draw.arc([center[0] - outer_radius, center[1] - outer_radius, center[0] + outer_radius,
                  center[1] + outer_radius],
                 start=start_angle, end=end_angle, fill="limegreen", width=20)

        icon_img = Image.open(self.icons[icon]).resize((outer_radius+20, outer_radius+20))
        image.paste(icon_img, (center[0] - icon_img.width // 2, center[1] - icon_img.height // 2), icon_img)


    def create_text(self, draw, text, position, font_size=30, color="black", bold=False, angle=0, base_image=None):
        """
        base_image only required for angle
        """
        if bold:
            font = ImageFont.truetype(self.bold_font_path, font_size)
        else:
            font = ImageFont.truetype(self.regular_font_path, font_size)

        if angle==0:
            draw.text(position, text, fill=color, font=font)
        else:
            lines = text.split("\n")
            line_spacing = 5
            line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
            total_text_height = sum(line_heights) + (line_spacing * (len(lines) - 1))
            max_text_width = max(font.getbbox(line)[2] - font.getbbox(line)[0] for line in lines)

            # Create a transparent image with the required size
            text_image = Image.new("RGBA", (max_text_width + 20, total_text_height + 20), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_image)

            # Draw each line at appropriate positions
            y_offset = 0
            for line in lines:
                text_draw.text((0, y_offset), line, font=font, fill=color)
                y_offset += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing  # Line spacing

            # Rotate the text image
            rotated_text = text_image.rotate(angle, expand=True)
            # Paste the rotated text onto the original image
            base_image.paste(rotated_text, position, rotated_text)

    @staticmethod
    def generate_weekly_data(data: pandas.DataFrame, n: int, metric: str) -> pandas.DataFrame :
        """
        Aggregate the data going back n weeks from today. Week starts from Monday and ensure missing weeks have a value 0
        """
        data["start_date_local"] = pandas.to_datetime(data["start_date_local"])
        data["week_start"] = data["start_date_local"].dt.tz_localize(None).dt.to_period("W-SUN").apply(lambda r: r.start_time)
        weekly_data = data.groupby("week_start")[metric].sum().reset_index()

        # Get the latest n weeks including the current week
        latest_week = pandas.Timestamp.today().normalize() - pandas.Timedelta(days=pandas.Timestamp.today().weekday())  # Monday of current week
        earliest_week = latest_week - pandas.Timedelta(weeks=n-1)
        all_weeks = pandas.date_range(start=earliest_week, end=latest_week, freq="W-MON")
        weekly_data = weekly_data.set_index("week_start").reindex(all_weeks, fill_value=0).reset_index()
        return weekly_data.rename(columns={"index": "week_start"})

    def generate_four_week_summary(self) -> list[list[str]]:
        """
        Returns the last four-week run and ride summaries
        """
        result = [
            ["Activities", f"{self.recent_stats["recent_run_totals.count"]:,.0f}", f"{self.recent_stats["recent_ride_totals.count"]:,.0f}"],
            ["Time", f"{self.format_time(self.recent_stats["recent_run_totals.elapsed_time"])}", f"{self.format_time(self.recent_stats["recent_ride_totals.moving_time"])}"],
            ["Distance", f"{self.recent_stats["recent_run_totals.distance"]/1000:,.1f}km", f"{self.recent_stats["recent_ride_totals.distance"]/1000:,.1f}km"],
            ["Elevation gain", f"{self.recent_stats["recent_run_totals.elevation_gain"]:,.1f}m", f"{self.recent_stats["recent_ride_totals.elevation_gain"]/1000:,.1f}km"]
        ]

        return result


    def create_line_chart(self, image, weekly_data, position, size, metric, is_time):
        fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100))

        # Plot the data with an orange line and circular markers
        ax.plot(weekly_data['week_start'], weekly_data[metric], marker='o', markersize=3, color='#ff6600', linewidth=2)
        ax.fill_between(weekly_data['week_start'], weekly_data[metric], color='#ff6600', alpha=0.3)

        # Set the y-axis to scale based on the highest value
        max_value = weekly_data[metric].max()
        ax.set_ylim(0, max_value * 1.03)  # Add 3% buffer

        # Formatting the x-axis to show only the beginning of the month
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        ax.set_xlim(weekly_data['week_start'].min(), weekly_data['week_start'].max())

        # Formatting the y-axis
        ax.set_yticks([max_value / 2, max_value])
        if is_time:
            ax.set_yticklabels([f"{self.format_time(max_value/2)}", f"{self.format_time(max_value)}"])
        else:
            ax.set_yticklabels([f"{max_value / 2:.1f} km", f"{max_value:.1f} km"])

        # Customizing appearance
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.tick_params(axis='x', colors="black", labelsize=8)
        ax.tick_params(axis='y', colors="black", labelsize=6, pad=2)
        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', facecolor="white")
        buf.seek(0)
        chart_img = Image.open(buf)
        image.paste(chart_img, position)

    def calculate_progress(self, ytd_finished, yearly_goal, is_time) -> str:
        today = datetime.today()
        day_of_year = today.timetuple().tm_yday
        total_days = 366 if today.year % 4 == 0 else 365

        expected_progress = (yearly_goal / total_days) * day_of_year
        difference = ytd_finished - expected_progress
        ahead_or_behind = "ahead of plan" if difference > 0 else "behind plan"
        if is_time:
            return f"{self.format_time(abs(difference*3600))} {ahead_or_behind}"
        return f"{abs(difference):,.1f}km {ahead_or_behind}"

    @staticmethod
    def format_time(seconds):
        """
        Convert seconds into a formatted string with hours and minutes rounded to the nearest integer.
        """
        hours = int(seconds // 3600)
        minutes = round((seconds % 3600) / 60)

        return f"{hours}h {minutes}m"


    def generate_run_summary_screen(self) -> Image:
            """
            Generate a running summary screen
            """
            image = Image.new("RGB", (400, 480), "white")
            draw = ImageDraw.Draw(image)

            progress = self.recent_stats["ytd_run_totals.distance"] / self.goals["yearly_running_distance"] / 1000
            self.progress_ring(image, progress=progress, center=(100, 90), outer_radius=80, icon="running_progress_shoe")

            text = f"{(1-progress) * self.goals['yearly_running_distance']:,.1f}km to go"
            self.create_text(draw=draw, text=text, position=(200, 60), font_size=16)

            text = f"{self.recent_stats["ytd_run_totals.distance"]/1000:,.1f}km / {self.goals["yearly_running_distance"]:,.1f}km"
            self.create_text(draw=draw, text=text, position=(200, 90), font_size=16)

            text = self.calculate_progress(ytd_finished=self.recent_stats["ytd_run_totals.distance"]/1000, yearly_goal=self.goals["yearly_running_distance"], is_time=False)
            self.create_text(draw=draw, text=text, position=(200, 120), font_size=16)

            #Add zigzags
            zigzag = Image.open(self.icons["zigzag"]).resize((30, 30)).convert("RGBA")
            for x in range(10, 390, 30):
                image.paste(zigzag, (x, 165), zigzag)
                image.paste(zigzag, (x, 305), zigzag)

            # Generate data for line chart
            run_history = self.activities.loc[self.activities["type"].isin(["Run"]), ["start_date_local", "distance"]]
            weekly_summary = self.generate_weekly_data(data=run_history, n=12, metric="distance")
            weekly_summary["distance"] /= 1000
            self.create_line_chart(image, weekly_summary, (20, 185), (370, 120), metric="distance", is_time=False)

            # image.save("output/run_summary.jpg")
            return image

    def generate_ride_summary_screen(self) -> Image:
            """
            Generate a running summary screen
            """
            image = Image.new("RGB", (400, 480), "white")
            draw = ImageDraw.Draw(image)

            progress = self.recent_stats["ytd_ride_totals.moving_time"] / self.goals["yearly_cycling_hours"] / 3600
            self.progress_ring(image, progress=progress, center=(100, 90), outer_radius=80, icon="cycling_progress_bike")

            text = f"{self.format_time( (1-progress) * self.goals['yearly_cycling_hours'] * 3600 )} to go"
            self.create_text(draw=draw, text=text, position=(200, 60), font_size=16)

            text = f"{self.format_time(self.recent_stats['ytd_ride_totals.moving_time'])} / {self.goals['yearly_cycling_hours']}h"
            self.create_text(draw=draw, text=text, position=(200, 90), font_size=16)

            text = self.calculate_progress(ytd_finished=self.recent_stats["ytd_ride_totals.moving_time"]/3600, yearly_goal=self.goals["yearly_cycling_hours"], is_time=True)
            self.create_text(draw=draw, text=text, position=(200, 120), font_size=16)

            #Add zigzags
            zigzag = Image.open(self.icons["zigzag"]).resize((30, 30)).convert("RGBA")
            for x in range(10, 390, 30):
                image.paste(zigzag, (x, 165), zigzag)
                image.paste(zigzag, (x, 305), zigzag)


            # Generate data for line chart
            ride_history = self.activities.loc[self.activities["type"].isin(["Ride", "VirtualRide"]), ["start_date_local", "moving_time"]]
            weekly_summary = self.generate_weekly_data(data=ride_history, n=12, metric="moving_time")
            self.create_line_chart(image, weekly_summary, (20, 185), (370, 120), metric="moving_time", is_time=True)

            # image.save("output/ride_summary.jpg")
            return image

    def add_combined_table(self, image, position) -> Image:
        """
        Draws a combined run and ride table on the given image at the specified position
        """
        draw = ImageDraw.Draw(image)
        data = self.generate_four_week_summary()
        font = ImageFont.truetype(self.bold_font_path, 13)

        col_widths = [120, 100, 100]  # Widths of table columns
        row_height = 23  # Height of each row

        x_start, y_start = position

        # Draw table headers
        headers = ["", "Runs", "Rides"]
        for i, header in enumerate(headers):
            draw.rectangle(
                [x_start + sum(col_widths[:i]), y_start, x_start + sum(col_widths[:i + 1]), y_start + row_height],
                outline="black",
                fill="lightgray"
            )
            text_x = x_start + sum(col_widths[:i]) + (col_widths[i] // 2)
            draw.text((text_x, y_start + 10), header, font=font, fill="black", anchor="mm")

        # Draw table rows
        for row_idx, row in enumerate(data):
            for col_idx, cell in enumerate(row):
                x1 = x_start + sum(col_widths[:col_idx])
                y1 = y_start + (row_idx + 1) * row_height
                x2 = x_start + sum(col_widths[:col_idx + 1])
                y2 = y_start + (row_idx + 2) * row_height

                draw.rectangle([x1, y1, x2, y2], outline="black", fill="white")

                text_x = x1 + (col_widths[col_idx] // 2)
                text_y = y1 + (row_height // 2)
                draw.text((text_x, text_y), str(cell), font=font, fill="black", anchor="mm")

        return image

    def get_quote(self) -> str:
        quotes = pandas.read_excel(self._input_data, sheet_name="quotes")
        return quotes.sample(n=1)["quote"].iloc[0]

    @staticmethod
    def get_run_time() -> str:
        et_now = datetime.now(tz=ZoneInfo("America/New_York"))
        return et_now.strftime("Run on %b %d, %y at %I:%M %p")

    @staticmethod
    def wrap_text(text, max_line_length):
        wrapped_text = textwrap.fill(text, width=max_line_length, break_long_words=False, break_on_hyphens=False)
        return wrapped_text

    def summary_screen(self) -> None:
        """
        Combines run and ride summaries
        """
        run_summary = self.generate_run_summary_screen()
        ride_summary = self.generate_ride_summary_screen()

        combined_width = run_summary.width + ride_summary.width
        combined_height = max(run_summary.height, ride_summary.height)

        combined_summary = Image.new('RGB', (combined_width, combined_height), "white")
        combined_summary.paste(run_summary, (0, 0))
        combined_summary.paste(ride_summary, (run_summary.width, 0))

        # Add common title
        draw = ImageDraw.Draw(combined_summary)
        self.create_text(draw=draw, text="Last 4 weeks", position=(100, 320), font_size=19, bold=True)

        # Add last 4 weeks summary
        self.add_combined_table(image=combined_summary, position=(15, 350))

        # Add motivational quote
        wrapped_quote = self.wrap_text(self.get_quote(), max_line_length=40)
        self.create_text(draw=draw, text=wrapped_quote, position=(340, 330), font_size=22, angle=8, base_image=combined_summary)

        # Add run time
        self.create_text(draw=draw, text=self.get_run_time(), position=(560, 450), font_size=9)

        combined_summary.save("output/combined_summary.jpg", format="JPEG")

    def race_calendar_screen(self) -> None:
        """
        Prints at most 3 upcoming races as well as the most recent completed race that has a strava post
        """
        # Load race calendar
        today = datetime.today()
        upcoming_races = self.race_calendar[self.race_calendar['date'] >= today].sort_values('date').head(3)
        past_races = self.race_calendar[(self.race_calendar['date'] < today) & (self.race_calendar['strava_event'] != "No")].sort_values('date', ascending=False).head(1)

        # Create image
        image = Image.new("RGB", (800, 480), "white")
        draw = ImageDraw.Draw(image)
        calendar_icon = Image.open(self.icons["calendar"]).resize((15, 15))
        location_icon = Image.open(self.icons["location"]).resize((15, 15))
        goal_icon = Image.open(self.icons["goal"]).resize((15, 15))

        self.create_text(draw, "Upcoming Races!!", (65, 10), font_size=25, bold=True)
        # Display upcoming races on the left half
        y_position = 50
        for _, race in upcoming_races.iterrows():
            try:
                logo = Image.open(f"{self._race_image_path}/{race['logo']}.JPG").resize((100, 100))
                image.paste(logo, (22, y_position))
            except:
                self.create_text(draw, "Logo", (22, y_position), font_size=20)

            # Calculate days left
            days_left = (race['date'] - today).days

            # Display race details
            self.create_text(draw, f"{race['race']}", (130, y_position), font_size=18, bold=True)
            image.paste(calendar_icon, (130, y_position + 33))
            self.create_text(draw, f" {race['date'].strftime('%b %d, %Y')} ({days_left} to go)", (142, y_position + 33), font_size=14)
            image.paste(location_icon, (130, y_position + 51))
            self.create_text(draw, f" {race['location']}", (142, y_position + 51), font_size=14)
            image.paste(goal_icon, (130, y_position + 69))
            self.create_text(draw, f" {race['goal']}", (142, y_position + 69), font_size=14)

            y_position += 105

        # Add race quote
        wrapped_quote = self.wrap_text(self.get_quote(), max_line_length=45)
        self.create_text(draw=draw, text=wrapped_quote, position=(20, y_position-20), font_size=20, angle=8, base_image=image)

        # Display most recent race on the right half
        if not past_races.empty:
            past_race = past_races.iloc[0]
            try:
                strava_img = Image.open(f"{self._race_image_path}/{past_race['strava_event']}.jpeg").resize((300, 450))
                image.paste(strava_img, (470, 20))
            except:
                self.create_text(draw, "No Strava post available", (600, 280), font_size=20)

        # Add run time
        self.create_text(draw=draw, text=self.get_run_time(), position=(80, 460), font_size=9)
        # Save and return the image
        image.save("output/race_calendar.jpg")


if __name__ == "__main__":
    obj = Strava()
    obj.summary_screen()
    obj.race_calendar_screen()
    print("Done")